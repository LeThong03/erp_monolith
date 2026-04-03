from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.models import UserRole
from app.modules.inventory.models import Ingredient
from app.modules.menu.models import MenuItem, RecipeLine
from app.modules.menu.schemas import (
    CostLineOut,
    MenuItemCostOut,
    MenuItemCreate,
    MenuItemOut,
    MenuItemUpdate,
)
from app.modules.purchasing.models import POStatus, PurchaseOrder, PurchaseOrderItem

router = APIRouter(prefix="/menu", tags=["Menu"])


def _get_item_or_404(item_id: int, db: Session) -> MenuItem:
    item = db.query(MenuItem).filter(MenuItem.id == item_id, MenuItem.is_active.is_(True)).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
    return item


def _validate_ingredients(ingredient_ids: list[int], db: Session) -> None:
    found = {r.id for r in db.query(Ingredient.id).filter(Ingredient.id.in_(ingredient_ids)).all()}
    missing = set(ingredient_ids) - found
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Ingredient IDs not found: {sorted(missing)}",
        )


@router.post(
    "/items",
    response_model=MenuItemOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.admin, UserRole.manager))],
)
def create_item(payload: MenuItemCreate, db: Session = Depends(get_db)):
    if payload.recipe_lines:
        _validate_ingredients([line.ingredient_id for line in payload.recipe_lines], db)

    item = MenuItem(
        name=payload.name.strip(),
        category=payload.category,
        selling_price=payload.selling_price,
    )
    db.add(item)
    db.flush()

    for line in payload.recipe_lines:
        db.add(RecipeLine(
            menu_item_id=item.id,
            ingredient_id=line.ingredient_id,
            qty_per_serving=line.qty_per_serving,
        ))

    db.commit()
    db.refresh(item)
    return item


@router.get(
    "/items",
    response_model=list[MenuItemOut],
    dependencies=[Depends(get_current_user)],
)
def list_items(db: Session = Depends(get_db)):
    return db.query(MenuItem).filter(MenuItem.is_active.is_(True)).order_by(MenuItem.name.asc()).all()


@router.get(
    "/items/{item_id}",
    response_model=MenuItemOut,
    dependencies=[Depends(get_current_user)],
)
def get_item(item_id: int, db: Session = Depends(get_db)):
    return _get_item_or_404(item_id, db)


@router.patch(
    "/items/{item_id}",
    response_model=MenuItemOut,
    dependencies=[Depends(require_role(UserRole.admin, UserRole.manager))],
)
def update_item(item_id: int, payload: MenuItemUpdate, db: Session = Depends(get_db)):
    item = _get_item_or_404(item_id, db)

    for field in ("name", "category", "selling_price"):
        value = getattr(payload, field)
        if value is not None:
            setattr(item, field, value)

    line_map = {line.id: line for line in item.recipe_lines}

    for line_id in (payload.lines_to_remove or []):
        if line_id not in line_map:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Recipe line ID {line_id} does not belong to this item",
            )
        db.delete(line_map.pop(line_id))

    for patch in (payload.lines_to_upsert or []):
        if patch.id is not None:
            if patch.id not in line_map:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Recipe line ID {patch.id} does not belong to this item",
                )
            line = line_map[patch.id]
            if patch.qty_per_serving is not None:
                line.qty_per_serving = patch.qty_per_serving
        else:
            if patch.ingredient_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="ingredient_id is required when adding a new recipe line",
                )
            _validate_ingredients([patch.ingredient_id], db)
            db.add(RecipeLine(
                menu_item_id=item.id,
                ingredient_id=patch.ingredient_id,
                qty_per_serving=patch.qty_per_serving or 0,
            ))

    db.commit()
    db.refresh(item)
    return item


@router.get(
    "/items/{item_id}/cost",
    response_model=MenuItemCostOut,
    dependencies=[Depends(get_current_user)],
)
def get_item_cost(item_id: int, db: Session = Depends(get_db)):
    item = _get_item_or_404(item_id, db)

    cost_lines: list[CostLineOut] = []
    total_cost = 0.0

    for line in item.recipe_lines:
        ingredient = db.query(Ingredient).filter(Ingredient.id == line.ingredient_id).first()

        # Last unit price from a received PO
        last_price = (
            db.query(PurchaseOrderItem.unit_price)
            .join(PurchaseOrder, PurchaseOrderItem.order_id == PurchaseOrder.id)
            .filter(
                PurchaseOrderItem.ingredient_id == line.ingredient_id,
                PurchaseOrder.status == POStatus.received.value,
                PurchaseOrderItem.unit_price.isnot(None),
            )
            .order_by(PurchaseOrder.received_at.desc())
            .scalar()
        )

        unit_price = float(last_price) if last_price is not None else None
        qty = float(line.qty_per_serving)
        line_cost = qty * (unit_price or 0.0)
        total_cost += line_cost

        cost_lines.append(CostLineOut(
            ingredient_id=line.ingredient_id,
            ingredient_name=ingredient.name,
            qty_per_serving=qty,
            unit_price=unit_price,
            line_cost=line_cost,
        ))

    selling_price = float(item.selling_price)
    return MenuItemCostOut(
        menu_item_id=item.id,
        selling_price=selling_price,
        theoretical_cost=total_cost,
        gross_margin=selling_price - total_cost,
        lines=cost_lines,
    )