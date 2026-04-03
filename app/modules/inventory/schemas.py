from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.modules.inventory.models import MovementType


class IngredientCreate(BaseModel):
    name: str
    unit: str
    name_vn: Optional[str] = None
    category: Optional[str] = None
    reorder_level: Optional[float] = None


class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    unit: Optional[str] = None
    name_vn: Optional[str] = None
    category: Optional[str] = None
    reorder_level: Optional[float] = None


class IngredientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    unit: str
    name_vn: Optional[str]
    category: Optional[str]
    quantity_in_stock: float = Field(validation_alias="stock_qty")
    reorder_level: Optional[float] = Field(validation_alias="par_level")
    is_active: bool


class StockAdjust(BaseModel):
    qty: float
    movement_type: MovementType
    note: Optional[str] = None


class StockMovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingredient_id: int
    qty: float
    movement_type: str
    note: Optional[str]
    created_at: datetime
    created_by_id: Optional[int]
