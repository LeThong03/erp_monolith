from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    selling_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true", nullable=False)

    recipe_lines: Mapped[list["RecipeLine"]] = relationship(
        "RecipeLine", back_populates="menu_item", cascade="all, delete-orphan"
    )


class RecipeLine(Base):
    __tablename__ = "recipe_lines"
    __table_args__ = (UniqueConstraint("menu_item_id", "ingredient_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), nullable=False, index=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"), nullable=False)
    qty_per_serving: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)

    menu_item: Mapped["MenuItem"] = relationship("MenuItem", back_populates="recipe_lines")