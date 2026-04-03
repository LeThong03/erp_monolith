from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.auth.router import router as auth_router
from app.modules.inventory.router import router as inventory_router
from app.modules.menu.router import router as menu_router
from app.modules.sales.router import router as sales_router
from app.modules.purchasing.router import router as purchasing_router

app = FastAPI(title="Restaurant ERP-lite (Monolith)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(inventory_router)
app.include_router(menu_router)
app.include_router(sales_router)
app.include_router(purchasing_router)


