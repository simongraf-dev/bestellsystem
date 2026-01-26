from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest
from app.schemas.user import UserResponse
from app.models import User
from app.utils.security import verify_password, create_access_token, create_refresh_token, decode_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Email oder Passwort falsch")
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email oder Passwort falsch")
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
)


@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(request: RefreshRequest):
    payload = decode_token(request.refresh_token, "refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Refresh Token abgelaufen")
    
    access_token = create_access_token({"sub": (payload.get("sub"))})
    refresh_token = create_refresh_token({"sub": (payload.get("sub"))})
        

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )

@router.get("/me", response_model = UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return user