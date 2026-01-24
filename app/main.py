from fastapi import FastAPI

from app.routers import auth
from app.config import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.include_router(auth.router)

@app.get("/")
def root() -> dict:
        return {"message": "Bestellsystem läuft!", "app": settings.app_name}

@app.get("/health")
def health() -> dict:
        return {"status": "ok"}