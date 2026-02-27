from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    unit: Mapped[str] = mapped_column(String(20))  # kg, g, litre, etc.