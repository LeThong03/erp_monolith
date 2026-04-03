from datetime import date, datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.models import User, UserRole
from app.modules.inventory.models import Ingredient, MovementType, StockMovement
from app.modules.menu.models import MenuItem
from app.modules.sales.models import SaleRecord
from app.modules.sales.schemas import SaleCreate, SaleOut, SaleSummaryLine, SaleSummaryOut

router = APIRouter(prefix="/sales", tags=["Sales"])


@router.post(
    "",
    response_model=SaleOut,
    status_code=status.HTTP_201_CREATED,
)
def record_sale(
    payload: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(MenuItem).filter(MenuItem.id == payload.menu_item_id, MenuItem.is_active.is_(True)).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")

    recorded_at = payload.recorded_at or datetime.now(timezone.utc)

    sale = SaleRecord(
        menu_item_id=item.id,
        qty_sold=payload.qty_sold,
        recorded_at=recorded_at,
        recorded_by_id=current_user.id,
    )
    db.add(sale)
    db.flush()

    for line in item.recipe_lines:
        total_qty = float(line.qty_per_serving) * payload.qty_sold

        ing = db.query(Ingredient).filter(Ingredient.id == line.ingredient_id).first()
        if ing:
            ing.stock_qty = float(ing.stock_qty) - total_qty
            db.add(StockMovement(
                ingredient_id=line.ingredient_id,
                qty=-total_qty,
                movement_type=MovementType.consumption.value,
                note=f"Sale #{sale.id} — {item.name} x{payload.qty_sold}",
                created_at=recorded_at,
                created_by_id=current_user.id,
            ))

    db.commit()
    db.refresh(sale)
    return sale


@router.get(
    "",
    response_model=list[SaleOut],
    dependencies=[Depends(get_current_user)],
)
def list_sales(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(SaleRecord)
    if from_date:
        q = q.filter(SaleRecord.recorded_at >= datetime(from_date.year, from_date.month, from_date.day, tzinfo=timezone.utc))
    if to_date:
        q = q.filter(SaleRecord.recorded_at < datetime(to_date.year, to_date.month, to_date.day + 1, tzinfo=timezone.utc))
    return q.order_by(SaleRecord.recorded_at.desc()).all()


@router.get(
    "/summary",
    response_model=SaleSummaryOut,
    dependencies=[Depends(get_current_user)],
)
def sales_summary(
    period: Literal["daily", "weekly"] = Query("daily"),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    trunc = func.date_trunc(period if period == "week" else "day", SaleRecord.recorded_at).label("period_start")

    q = (
        db.query(
            trunc,
            func.sum(SaleRecord.qty_sold).label("total_qty_sold"),
            func.sum(SaleRecord.qty_sold * MenuItem.selling_price).label("total_revenue"),
        )
        .join(MenuItem, SaleRecord.menu_item_id == MenuItem.id)
    )

    if from_date:
        q = q.filter(SaleRecord.recorded_at >= datetime(from_date.year, from_date.month, from_date.day, tzinfo=timezone.utc))
    if to_date:
        q = q.filter(SaleRecord.recorded_at < datetime(to_date.year, to_date.month, to_date.day + 1, tzinfo=timezone.utc))

    rows = q.group_by("period_start").order_by("period_start").all()

    return SaleSummaryOut(
        period=period,
        from_date=from_date,
        to_date=to_date,
        totals=[
            SaleSummaryLine(
                period_start=row.period_start,
                total_qty_sold=float(row.total_qty_sold),
                total_revenue=float(row.total_revenue),
            )
            for row in rows
        ],
    )
