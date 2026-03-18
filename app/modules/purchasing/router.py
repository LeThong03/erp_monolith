from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.models import User, UserRole
from app.modules.inventory.models import Ingredient, MovementType, StockMovement
from app.modules.purchasing.models import POStatus, PurchaseOrder, PurchaseOrderItem, Supplier
from app.modules.purchasing.schemas import (
    POCreate,
    POOut,
    ReceivePOIn,
    SupplierCreate,
    SupplierOut,
)

router = APIRouter(prefix="/purchasing", tags=["Purchasing"])


def _get_po_or_404(id: int, db: Session) -> PurchaseOrder:
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == id).first()
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found")
    return po


# ── Suppliers ──────────────────────────────────────────────────────────────────

@router.post(
    "/suppliers",
    response_model=SupplierOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.admin, UserRole.manager))],
)
def create_supplier(payload: SupplierCreate, db: Session = Depends(get_db)):
    supplier = Supplier(
        name=payload.name.strip(),
        contact_name=payload.contact_name,
        phone=payload.phone,
        email=payload.email,
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get(
    "/suppliers",
    response_model=list[SupplierOut],
    dependencies=[Depends(get_current_user)],
)
def list_suppliers(db: Session = Depends(get_db)):
    return db.query(Supplier).order_by(Supplier.name.asc()).all()


@router.patch(
    "/suppliers/{id}",
    response_model=SupplierOut,
    dependencies=[Depends(require_role(UserRole.admin, UserRole.manager))],
)
def update_supplier(id: int, payload: SupplierCreate, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.id == id).first()
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)
    db.commit()
    db.refresh(supplier)
    return supplier


# ── Purchase Orders ────────────────────────────────────────────────────────────

@router.post(
    "/orders",
    response_model=POOut,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    payload: POCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.manager)),
):
    if not db.query(Supplier).filter(Supplier.id == payload.supplier_id, Supplier.is_active.is_(True)).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")

    ingredient_ids = [item.ingredient_id for item in payload.items]
    found_ids = {r.id for r in db.query(Ingredient.id).filter(Ingredient.id.in_(ingredient_ids)).all()}
    missing = set(ingredient_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Ingredient IDs not found: {sorted(missing)}",
        )

    po = PurchaseOrder(
        supplier_id=payload.supplier_id,
        status=POStatus.draft.value,
        note=payload.note,
        created_at=datetime.now(timezone.utc),
        created_by_id=current_user.id,
    )
    db.add(po)
    db.flush()

    for item_in in payload.items:
        db.add(PurchaseOrderItem(
            order_id=po.id,
            ingredient_id=item_in.ingredient_id,
            qty_ordered=item_in.qty_ordered,
            unit_price=item_in.unit_price,
        ))

    db.commit()
    db.refresh(po)
    return po


@router.get(
    "/orders",
    response_model=list[POOut],
    dependencies=[Depends(get_current_user)],
)
def list_orders(db: Session = Depends(get_db)):
    return db.query(PurchaseOrder).order_by(PurchaseOrder.created_at.desc()).all()


@router.get(
    "/orders/{id}",
    response_model=POOut,
    dependencies=[Depends(get_current_user)],
)
def get_order(id: int, db: Session = Depends(get_db)):
    return _get_po_or_404(id, db)


@router.post("/orders/{id}/submit", response_model=POOut)
def submit_order(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.manager)),
):
    po = _get_po_or_404(id, db)
    if po.status != POStatus.draft.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only draft orders can be submitted (current status: {po.status})",
        )
    po.status = POStatus.submitted.value
    po.ordered_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(po)
    return po


@router.post("/orders/{id}/receive", response_model=POOut)
def receive_order(
    id: int,
    payload: ReceivePOIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.manager)),
):
    po = _get_po_or_404(id, db)
    if po.status != POStatus.submitted.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only submitted orders can be received (current status: {po.status})",
        )

    item_map = {item.id: item for item in po.items}
    received_ids = {r.item_id for r in payload.items}
    unknown = received_ids - item_map.keys()
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Item IDs not in this order: {sorted(unknown)}",
        )

    now = datetime.now(timezone.utc)
    for receive_in in payload.items:
        line = item_map[receive_in.item_id]
        line.qty_received = receive_in.qty_received

        ing = db.query(Ingredient).filter(Ingredient.id == line.ingredient_id).first()
        ing.stock_qty = float(ing.stock_qty) + receive_in.qty_received

        db.add(StockMovement(
            ingredient_id=line.ingredient_id,
            qty=receive_in.qty_received,
            movement_type=MovementType.restock.value,
            note=f"PO #{po.id}",
            created_at=now,
            created_by_id=current_user.id,
        ))

    po.status = POStatus.received.value
    po.received_at = now
    db.commit()
    db.refresh(po)
    return po


@router.post("/orders/{id}/cancel", response_model=POOut)
def cancel_order(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.manager)),
):
    po = _get_po_or_404(id, db)
    if po.status not in (POStatus.draft.value, POStatus.submitted.value):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel an order with status: {po.status}",
        )
    po.status = POStatus.cancelled.value
    db.commit()
    db.refresh(po)
    return po
