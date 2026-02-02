from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, article, article_groups, users, department, supplier, roles, orders, delivery_days, article_supplier, shipping_groups, approver_supplier, order_items
from app.config import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(article.router)
app.include_router(article_groups.router)
app.include_router(roles.router)
app.include_router(department.router)
app.include_router(users.router)
app.include_router(supplier.router)
app.include_router(orders.router)
app.include_router(delivery_days.router)
app.include_router(article_supplier.router)
app.include_router(shipping_groups.router)
app.include_router(approver_supplier.router)
app.include_router(order_items.router)

@app.get("/")
def root() -> dict:
        return {"message": "Bestellsystem läuft!", "app": settings.app_name}

@app.get("/health")
def health() -> dict:
        return {"status": "ok"}