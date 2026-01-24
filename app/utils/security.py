from passlib.context import CryptContext

from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from app.config import settings


# Password
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# JWT

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode['exp'] = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode['type'] = 'access'
    return jwt.encode(to_encode, settings.secret_key, settings.jwt_algorithm)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode['exp'] = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    to_encode['type'] = 'refresh'
    return jwt.encode(to_encode, settings.secret_key, settings.jwt_algorithm)

def decode_token(token: str, expected_type: str = None) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        if expected_type and payload.get('type') != expected_type:
            return None
        return payload
    except JWTError:
        return None