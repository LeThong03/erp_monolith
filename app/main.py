from fastapi import FastAPI
from app.modules.inventory.router import router as inventory_router

app = FastAPI(title="Restaurant ERP-lite (Monolith)")

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(inventory_router)