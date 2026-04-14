"""
backend/src/auth.py
JWT authentication using python-jose HS256.
Provides encode/decode functions and a FastAPI dependency.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from .config import settings

security = HTTPBearer()


class TokenClaims(BaseModel):
    """JWT token claims."""
    sub: str                    # user_id (UUID string)
    username: str
    role: str                   # admin | leader | officer | public_viewer
    clearance_level: int        # 0-3 (matches ClearanceLevel enum)
    departments: list[str]      # org_ids the user belongs to
    exp: datetime


def create_access_token(
    user_id: str,
    username: str,
    role: str,
    clearance_level: int,
    departments: list[str],
) -> str:
    """Create a JWT access token."""
    now = datetime.now(timezone.utc)
    claims = {
        "sub": user_id,
        "username": username,
        "role": role,
        "clearance_level": clearance_level,
        "departments": departments,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
        "iat": now,
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> TokenClaims:
    """Decode and validate a JWT token. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return TokenClaims(**payload)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> TokenClaims:
    """FastAPI dependency: extract and validate JWT from Authorization header."""
    return decode_token(credentials.credentials)


# Alias for type hints in route functions
CurrentUser = Annotated[TokenClaims, Depends(get_current_user)]


def require_role(*allowed_roles: str):
    """Factory for a dependency that checks the user's role."""
    async def checker(user: CurrentUser) -> TokenClaims:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' not in allowed roles: {allowed_roles}",
            )
        return user
    return checker


def require_clearance(min_level: int):
    """Factory for a dependency that checks the user's clearance level."""
    async def checker(user: CurrentUser) -> TokenClaims:
        if user.clearance_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Clearance level {user.clearance_level} < required {min_level}",
            )
        return user
    return checker
