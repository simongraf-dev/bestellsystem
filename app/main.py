from fastapi import FastAPI

from app.config import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)

@app.get("/")
def root() -> dict:
        return {"message": "Bestellsystem läuft!", "app": settings.app_name}

@app.get("/health")
def health() -> dict:
        return {"status": "ok"}