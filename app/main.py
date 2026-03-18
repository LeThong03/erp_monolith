from fastapi import FastAPI

from app.modules.auth.router import router as auth_router
from app.modules.inventory.router import router as inventory_router
from app.modules.purchasing.router import router as purchasing_router

app = FastAPI(title="Restaurant ERP-lite (Monolith)")


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(inventory_router)
app.include_router(purchasing_router)


