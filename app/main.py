
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, article, article_groups, users, department, supplier, orders, delivery_days, article_supplier, shipping_groups, approver_supplier, order_items, storage_location, article_storage_location, roles, activities, reservations
from app.config import settings
from app.utils.logging_config import setup_logging
from app.middleware.logging_middleware import log_requests


logger = setup_logging()
logger.info("Application starting...")
app = FastAPI(title=settings.app_name, debug=settings.debug)

app.middleware("http")(log_requests)

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
app.include_router(storage_location.router)
app.include_router(article_storage_location.router)
app.include_router(activities.router)
app.include_router(reservations.router)

@app.get("/")
def root() -> dict:
        return {"message": "Bestellsystem läuft!", "app": settings.app_name}

@app.get("/health")
def health() -> dict:
        return {"status": "ok"}