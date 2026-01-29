from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import pyotp

from app.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, TwoFactorSetupResponse, TwoFactorSetupVerifyRequest, LoginResponse, TwoFactorValidateRequest
from app.schemas.user import UserResponse
from app.models import User
from app.utils.security import verify_password, create_access_token, create_refresh_token, decode_token, get_current_user, require_role, create_temporary_token
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# Login und Prüfung auf 2FA
@router.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Email oder Passwort falsch")
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email oder Passwort falsch")
    if user.is_2fa_enabled:
        temp_token = create_temporary_token({"sub": str(user.id)})
        return LoginResponse(
            temp_token=temp_token,
            requires_2fa=True
        )
    # Wenn keine 2FA enabled, direkt access und refresh token ausstellen
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        requires_2fa=False
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
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# 2FA-Auth

@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
def two_fa_auth_setup(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.totp_secret:
        raise HTTPException(status_code=403, detail="2FA-Auth bereits eingerichtet")
    secret = pyotp.random_base32()
    current_user.totp_secret = secret
    db.add(current_user)
    db.commit()

    totp = pyotp.TOTP(secret)
    qr_url = totp.provisioning_uri(name=current_user.email, issuer_name=settings.two_factor_issuer)
    return TwoFactorSetupResponse(
        secret=secret,
        qr_url = qr_url

    )
    
@router.post("/2fa/verify")
def two_fa_setup_verification(entered_code: TwoFactorSetupVerifyRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    if not current_user.totp_secret:
        raise HTTPException(status_code=403, detail="Kein Secret vorhanden")
    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(entered_code.code):
        raise HTTPException(status_code=403, detail="Code ungültig")
    current_user.is_2fa_enabled = True
    db.add(current_user)
    db.commit()
    return {"message": "2FA erfolgreich eingerichtet"}


@router.post("/2fa/validate", response_model=TokenResponse)
def validate_otp(request: TwoFactorValidateRequest, db: Session = Depends(get_db)):
    payload = decode_token(request.temp_token, "temp",)
    if not payload:
        raise HTTPException(status_code=401, detail="Temporary Token abgelaufen")
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=403, detail="User nicht in Datenbank")

    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(request.code):
        raise HTTPException(status_code=403, detail="Code ungültig")
    
    access_token = create_access_token({"sub": (payload.get("sub"))})
    refresh_token = create_refresh_token({"sub": (payload.get("sub"))})
        

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


    