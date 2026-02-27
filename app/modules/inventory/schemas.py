from pydantic import BaseModel

class IngredientCreate(BaseModel):
    name: str
    unit: str

class IngredientOut(BaseModel):
    id: int
    name: str
    unit: str

    class Config:
        from_attributes = True