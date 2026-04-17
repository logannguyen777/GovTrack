"""
backend/src/auth.py
JWT authentication using python-jose HS256.
Provides encode/decode functions and a FastAPI dependency.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from .config import settings
from .models.enums import ClearanceLevel, Role

logger = logging.getLogger("govflow.auth")

security = HTTPBearer()

# ---------------------------------------------------------------------------
# LRU-style revocation cache (dict keyed by jti; value: True = revoked)
# Cache TTL: 30 seconds.  Entries are evicted lazily or on explicit pop().
# ---------------------------------------------------------------------------
_revocation_cache: dict[str, tuple[bool, float]] = {}  # jti -> (revoked, cached_at)
_REVOCATION_CACHE_TTL = 30.0  # seconds


def _cache_get(jti: str) -> bool | None:
    """Return cached revocation status or None if absent / stale."""
    entry = _revocation_cache.get(jti)
    if entry is None:
        return None
    revoked, cached_at = entry
    if time.monotonic() - cached_at > _REVOCATION_CACHE_TTL:
        _revocation_cache.pop(jti, None)
        return None
    return revoked


def _cache_set(jti: str, revoked: bool) -> None:
    _revocation_cache[jti] = (revoked, time.monotonic())


class TokenClaims(BaseModel):
    """JWT token claims."""

    sub: str  # user_id (UUID string)
    username: str
    role: str  # admin | leader | officer | staff_intake | staff_processor | legal | security
    clearance_level: int  # 0-3 (matches ClearanceLevel enum)
    departments: list[str]  # org_ids the user belongs to
    exp: datetime
    jti: str = ""  # JWT ID for revocation tracking


def create_access_token(
    user_id: str,
    username: str,
    role: str,
    clearance_level: int,
    departments: list[str],
) -> str:
    """Create a JWT access token with a unique jti claim."""
    now = datetime.now(UTC)
    claims = {
        "sub": user_id,
        "username": username,
        "role": role,
        "clearance_level": clearance_level,
        "departments": departments,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
        "iat": now,
        "jti": str(uuid.uuid4()),
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


async def _is_token_revoked(jti: str, exp: datetime) -> bool:
    """Check whether a token jti has been revoked.

    Uses a 30-second LRU cache to avoid a DB round-trip on every request.
    Returns False immediately for tokens without a jti (pre-0.2 tokens).
    """
    if not jti:
        return False

    cached = _cache_get(jti)
    if cached is not None:
        return cached

    # Query Postgres
    try:
        from .database import pg_connection

        async with pg_connection() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM revoked_tokens WHERE jti = $1 LIMIT 1",
                jti,
            )
        revoked = row is not None
    except Exception as exc:
        # If DB is unavailable, fail-open (allow token) but log loudly
        logger.error("Revocation DB check failed for jti=%s: %s", jti, exc)
        revoked = False

    _cache_set(jti, revoked)
    return revoked


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> TokenClaims:
    """FastAPI dependency: extract, validate, and revocation-check JWT."""
    claims = decode_token(credentials.credentials)

    if await _is_token_revoked(claims.jti, claims.exp):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return claims


# Alias for type hints in route functions
CurrentUser = Annotated[TokenClaims, Depends(get_current_user)]


# ---------------------------------------------------------------------------
# UserSession: lightweight context object propagated to graph layer
# ---------------------------------------------------------------------------

@dataclass
class UserSession:
    """
    Caller identity context passed to PermittedGremlinClient.

    Carries only what the permission engine needs: user_id, role, clearance.
    Created from TokenClaims for authenticated requests, or from the PUBLIC /
    SYSTEM sentinel constants for unauthenticated / internal paths.
    """
    user_id: str
    username: str
    role: str
    clearance: ClearanceLevel
    departments: list[str] = field(default_factory=list)
    # Distinguish special sentinel sessions in audit logs
    is_public: bool = False
    is_system: bool = False

    @classmethod
    def from_token(cls, claims: TokenClaims) -> "UserSession":
        return cls(
            user_id=claims.sub,
            username=claims.username,
            role=claims.role,
            clearance=ClearanceLevel(claims.clearance_level),
            departments=list(claims.departments),
        )


# Sentinel: unauthenticated citizen requests (public portal)
PUBLIC_SESSION = UserSession(
    user_id="__public__",
    username="anonymous",
    role=Role.PUBLIC_VIEWER,
    clearance=ClearanceLevel.UNCLASSIFIED,
    is_public=True,
)

# Sentinel: internal system / maintenance calls (full clearance, audit-logged distinctly)
SYSTEM_SESSION = UserSession(
    user_id="__system__",
    username="system",
    role=Role.ADMIN,
    clearance=ClearanceLevel.TOP_SECRET,
    is_system=True,
)


async def get_current_session(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> UserSession:
    """FastAPI dependency: returns a UserSession for the authenticated caller."""
    claims = await get_current_user(credentials)
    return UserSession.from_token(claims)


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
