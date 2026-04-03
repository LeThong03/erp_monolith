from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SupplierCreate(BaseModel):
    name: str
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    contact_name: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    is_active: bool


class POItemCreate(BaseModel):
    ingredient_id: int
    qty_ordered: float
    unit_price: Optional[float] = None


class POItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingredient_id: int
    qty_ordered: float
    qty_received: Optional[float]
    unit_price: Optional[float]


class POCreate(BaseModel):
    supplier_id: int
    note: Optional[str] = None
    items: list[POItemCreate]


class POOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_id: int
    status: str
    note: Optional[str]
    ordered_at: Optional[datetime]
    received_at: Optional[datetime]
    created_at: datetime
    created_by_id: int
    items: list[POItemOut]


class POItemPatch(BaseModel):
    id: Optional[int] = None          # omit to add a new line; provide to update existing
    ingredient_id: Optional[int] = None  # required when id is None (new line)
    qty_ordered: Optional[float] = None
    unit_price: Optional[float] = None


class POUpdate(BaseModel):
    note: Optional[str] = None
    items_to_upsert: Optional[list[POItemPatch]] = None  # add or update lines
    items_to_remove: Optional[list[int]] = None          # existing item IDs to delete


class ReceiveItemIn(BaseModel):
    item_id: int
    qty_received: float


class ReceivePOIn(BaseModel):
    items: list[ReceiveItemIn]
