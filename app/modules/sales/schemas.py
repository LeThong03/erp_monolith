from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class SaleCreate(BaseModel):
    menu_item_id: int
    qty_sold: float
    recorded_at: Optional[datetime] = None  # defaults to now if omitted


class SaleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    menu_item_id: int
    qty_sold: float
    recorded_at: datetime
    recorded_by_id: int


class SaleSummaryLine(BaseModel):
    period_start: datetime
    total_qty_sold: float
    total_revenue: float


class SaleSummaryOut(BaseModel):
    period: Literal["daily", "weekly"]
    from_date: Optional[date]
    to_date: Optional[date]
    totals: list[SaleSummaryLine]
