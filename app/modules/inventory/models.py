import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MovementType(str, enum.Enum):
    restock = "restock"
    consumption = "consumption"
    waste = "waste"
    adjustment = "adjustment"


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name_vn: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    unit: Mapped[str] = mapped_column(String(20))
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    stock_qty: Mapped[float] = mapped_column(
        Numeric(10, 3), default=0.0, server_default="0", nullable=False
    )
    par_level: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id"), nullable=False, index=True
    )
    qty: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)  # + in, - out
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )