"""Security utilities for authentication and encryption."""

import secrets
from datetime import datetime, timedelta
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.utils.datetime_utils import utc_now

# Password hashing context using Argon2
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = utc_now() + expires_delta
    else:
        expire = utc_now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return encoded_jwt


def create_refresh_token(user_id: str) -> tuple[str, str, datetime]:
    """
    Create a JWT refresh token.

    Args:
        user_id: User ID to encode in token

    Returns:
        Tuple of (token, jti, expiration)
    """
    jti = secrets.token_urlsafe(32)  # Unique token ID
    expire = utc_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    data = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh",
        "jti": jti,
    }

    token = jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return token, jti, expire


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT token.

    Args:
        token: JWT token to decode

    Returns:
        Decoded token payload

    Raises:
        JWTError: If token is invalid or expired
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    return payload


def generate_random_token(length: int = 32) -> str:
    """
    Generate a random URL-safe token.

    Args:
        length: Number of random bytes (default 32)

    Returns:
        URL-safe random token
    """
    return secrets.token_urlsafe(length)
