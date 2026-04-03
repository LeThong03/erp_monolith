from typing import Optional

from pydantic import BaseModel, ConfigDict


class RecipeLineCreate(BaseModel):
    ingredient_id: int
    qty_per_serving: float


class RecipeLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingredient_id: int
    qty_per_serving: float


class MenuItemCreate(BaseModel):
    name: str
    category: Optional[str] = None
    selling_price: float
    recipe_lines: list[RecipeLineCreate] = []


class MenuItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: Optional[str]
    selling_price: float
    is_active: bool
    recipe_lines: list[RecipeLineOut]


class RecipeLinePatch(BaseModel):
    id: Optional[int] = None           # omit to add a new line; provide to update existing
    ingredient_id: Optional[int] = None  # required when id is None
    qty_per_serving: Optional[float] = None


class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    selling_price: Optional[float] = None
    lines_to_upsert: Optional[list[RecipeLinePatch]] = None
    lines_to_remove: Optional[list[int]] = None  # RecipeLine IDs to delete


class CostLineOut(BaseModel):
    ingredient_id: int
    ingredient_name: str
    qty_per_serving: float
    unit_price: Optional[float]        # None if no received PO exists for this ingredient
    line_cost: float


class MenuItemCostOut(BaseModel):
    menu_item_id: int
    selling_price: float
    theoretical_cost: float
    gross_margin: float                # selling_price - theoretical_cost
    lines: list[CostLineOut]
