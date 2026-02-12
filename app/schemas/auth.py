from pydantic import BaseModel, Field
from typing import Optional

MIN_PASSWORD_LENGTH=8

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str ="bearer"

class LoginResponse(BaseModel):
    # normaler Login
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = "bearer"

    # 2FA Login
    temp_token: Optional[str] = None
    requires_2fa: bool = False

class TwoFactorValidateRequest(BaseModel):
    temp_token: str
    code: str

class RefreshRequest(BaseModel):
    refresh_token: str


class TwoFactorSetupResponse(BaseModel):
    secret: str
    qr_url: str

# Bestätigung das beim Setup der QR Code gescannt wurde
class TwoFactorSetupVerifyRequest(BaseModel):
    code: str

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH)