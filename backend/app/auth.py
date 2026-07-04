"""
JWT token creation/verification and password hashing utilities.

- JWT: HS256 with configurable expiration, issued by python-jose
- Password: bcrypt hashing via passlib
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# bcrypt context — auto-detects the best available bcrypt implementation
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Algorithm used for JWT signing
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash a plain-text password with bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plain-text password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_minutes: Optional[int] = None) -> str:
    """Create a JWT access token.

    Args:
        data: Payload to encode (must contain "sub" for user identifier).
        expires_minutes: Token lifetime in minutes. Defaults to JWT_EXPIRE_MINUTES setting.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire_minutes = expires_minutes or settings.JWT_EXPIRE_MINUTES
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token.

    Returns:
        The token payload if valid, or None if expired/invalid.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_reset_token() -> str:
    """Generate a secure random token for password reset."""
    return secrets.token_urlsafe(32)


def generate_verification_code() -> str:
    """Generate a 6-digit verification code."""
    return str(secrets.randbelow(900000) + 100000)
