from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.inventory.models import Ingredient
from app.modules.inventory.schemas import IngredientCreate, IngredientOut

router = APIRouter(prefix="/inventory", tags=["Inventory"])

@router.post("/ingredients", response_model=IngredientOut)
def create_ingredient(payload: IngredientCreate, db: Session = Depends(get_db)):
    ing = Ingredient(name=payload.name.strip(), unit=payload.unit.strip())
    db.add(ing)
    db.commit()
    db.refresh(ing)
    return ing

@router.get("/ingredients", response_model=list[IngredientOut])
def list_ingredients(db: Session = Depends(get_db)):
    return db.query(Ingredient).order_by(Ingredient.id.asc()).all()