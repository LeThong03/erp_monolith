from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.models import User, UserRole
from app.modules.inventory.models import Ingredient, StockMovement
from app.modules.inventory.schemas import (
    IngredientCreate,
    IngredientOut,
    IngredientUpdate,
    StockAdjust,
    StockMovementOut,
)

router = APIRouter(prefix="/inventory", tags=["Inventory"])


def _get_ingredient_or_404(id: int, db: Session) -> Ingredient:
    ing = db.query(Ingredient).filter(Ingredient.id == id, Ingredient.is_active.is_(True)).first()
    if not ing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingredient not found")
    return ing


@router.post(
    "/ingredients",
    response_model=IngredientOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.admin, UserRole.manager))],
)
def create_ingredient(payload: IngredientCreate, db: Session = Depends(get_db)):
    ing = Ingredient(
        name=payload.name.strip(),
        unit=payload.unit.strip(),
        name_vn=payload.name_vn.strip() if payload.name_vn else None,
        category=payload.category,
        par_level=payload.reorder_level,
    )
    db.add(ing)
    db.commit()
    db.refresh(ing)
    return ing


@router.get(
    "/ingredients",
    response_model=list[IngredientOut],
    dependencies=[Depends(get_current_user)],
)
def list_ingredients(db: Session = Depends(get_db)):
    return db.query(Ingredient).filter(Ingredient.is_active.is_(True)).order_by(Ingredient.id.asc()).all()


@router.delete(
    "/ingredients/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.admin, UserRole.manager))],
)
def delete_ingredient(id: int, db: Session = Depends(get_db)):
    ing = _get_ingredient_or_404(id, db)
    ing.is_active = False
    db.commit()


@router.put(
    "/ingredients/{id}",
    response_model=IngredientOut,
    dependencies=[Depends(require_role(UserRole.admin, UserRole.manager))],
)
@router.get(
    "/ingredients/{id}",
    response_model=IngredientOut,
    dependencies=[Depends(get_current_user)],
)
def get_ingredient(id: int, db: Session = Depends(get_db)):
    return _get_ingredient_or_404(id, db)


@router.patch(
    "/ingredients/{id}",
    response_model=IngredientOut,
    dependencies=[Depends(require_role(UserRole.admin, UserRole.manager))],
)
def update_ingredient(id: int, payload: IngredientUpdate, db: Session = Depends(get_db)):
    ing = _get_ingredient_or_404(id, db)
    data = payload.model_dump(exclude_unset=True)
    if "reorder_level" in data:
        data["par_level"] = data.pop("reorder_level")
    for field, value in data.items():
        setattr(ing, field, value)
    db.commit()
    db.refresh(ing)
    return ing


@router.post(
    "/ingredients/{id}/adjust",
    response_model=StockMovementOut,
    status_code=status.HTTP_201_CREATED,
)
def adjust_stock(
    id: int,
    payload: StockAdjust,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.manager)),
):
    ing = _get_ingredient_or_404(id, db)
    ing.stock_qty = float(ing.stock_qty) + payload.qty
    movement = StockMovement(
        ingredient_id=id,
        qty=payload.qty,
        movement_type=payload.movement_type.value,
        note=payload.note,
        created_at=datetime.now(timezone.utc),
        created_by_id=current_user.id,
    )
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement


@router.get(
    "/ingredients/{id}/movements",
    response_model=list[StockMovementOut],
    dependencies=[Depends(get_current_user)],
)
def list_movements(id: int, db: Session = Depends(get_db)):
    _get_ingredient_or_404(id, db)
    return (
        db.query(StockMovement)
        .filter(StockMovement.ingredient_id == id)
        .order_by(StockMovement.created_at.desc())
        .all()
    )


@router.get(
    "/low-stock",
    response_model=list[IngredientOut],
    dependencies=[Depends(get_current_user)],
)
def low_stock(db: Session = Depends(get_db)):
    return (
        db.query(Ingredient)
        .filter(
            Ingredient.par_level.isnot(None),
            Ingredient.stock_qty <= Ingredient.par_level,
        )
        .order_by(Ingredient.name.asc())
        .all()
    )