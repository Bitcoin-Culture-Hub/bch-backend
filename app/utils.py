from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from .config import settings

# password hashing
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return _pwd.hash(password)

def verify_password(plain_pw: str, hashed_pw: str) -> bool:
    return _pwd.verify(plain_pw, hashed_pw)

# JWT helpers
def create_access_token(data: dict, minutes: int | None = None) -> str:
    """Return a signed JWT access token with 'sub' claim in data."""
    exp_minutes = minutes if minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    expire = datetime.now(timezone.utc) + timedelta(minutes=exp_minutes)
    payload = data.copy()
    payload.update({"exp": int(expire.timestamp()), "type": "access"})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode and validate a JWT, raising JWTError on failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])