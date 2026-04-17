"""backend/src/api/auth_login.py -- Login and logout endpoints."""

import hashlib
import logging

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..auth import create_access_token, decode_token
from ..database import pg_connection
from ..models.schemas import LoginRequest, LoginResponse

logger = logging.getLogger("govflow.auth")

router = APIRouter(prefix="/auth", tags=["Auth"])

_ph = PasswordHasher()
_security = HTTPBearer()

# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------


def _verify_password(stored_hash: str, plaintext: str) -> bool:
    """Verify password against stored hash.

    Supports two hash formats for migration:
    - Argon2 hashes (start with ``$argon2``) — verified with argon2-cffi.
    - Legacy SHA-256 hex digests (64 hex chars) — fallback for existing DB rows.

    Returns True if password matches, False otherwise.
    """
    if stored_hash.startswith("$argon2"):
        try:
            return _ph.verify(stored_hash, plaintext)
        except VerifyMismatchError:
            return False
        except Exception:
            return False
    # Legacy SHA-256 fallback
    sha256_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    return stored_hash == sha256_hash


def _needs_rehash(stored_hash: str) -> bool:
    """Return True if the stored hash is a legacy SHA-256 that should be upgraded."""
    return not stored_hash.startswith("$argon2")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    """Authenticate and return JWT.

    On first login after migration: if stored hash is still SHA-256, verify
    the plaintext, then upgrade the stored hash to Argon2 in-place.
    """
    async with pg_connection() as conn:
        row = await conn.fetchrow(
            "SELECT id, username, full_name, role, clearance_level, "
            "departments, password_hash "
            "FROM users WHERE username = $1 AND is_active = TRUE",
            body.username,
        )

    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    stored_hash = row["password_hash"]

    if not _verify_password(stored_hash, body.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Upgrade legacy SHA-256 hash to Argon2 on successful login
    if _needs_rehash(stored_hash):
        new_hash = _ph.hash(body.password)
        try:
            async with pg_connection() as conn:
                await conn.execute(
                    "UPDATE users SET password_hash = $1 WHERE username = $2",
                    new_hash,
                    body.username,
                )
            logger.info("Upgraded password hash to Argon2 for user: %s", body.username)
        except Exception as exc:
            # Non-fatal: user is already authenticated; log and continue
            logger.warning("Failed to upgrade password hash for %s: %s", body.username, exc)

    token = create_access_token(
        user_id=str(row["id"]),
        username=row["username"],
        role=row["role"],
        clearance_level=row["clearance_level"],
        departments=list(row["departments"]),
    )

    return LoginResponse(
        access_token=token,
        user_id=str(row["id"]),
        role=row["role"],
        clearance_level=row["clearance_level"],
        full_name=row["full_name"] or "",
    )


@router.post("/logout", status_code=200)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
):
    """Revoke the current JWT by inserting its jti into the revoked_tokens table."""
    from ..auth import _revocation_cache

    token_str = credentials.credentials
    try:
        claims = decode_token(token_str)
    except HTTPException:
        # Token already invalid — accept logout gracefully
        return {"detail": "Logged out"}

    jti = getattr(claims, "jti", None)
    if not jti:
        # Token has no jti claim (e.g., issued before 0.2 patch) — can't revoke
        return {"detail": "Logged out (no jti)"}

    try:
        async with pg_connection() as conn:
            await conn.execute(
                """
                INSERT INTO revoked_tokens (jti, user_id, expires_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (jti) DO NOTHING
                """,
                jti,
                claims.sub,
                claims.exp,
            )
        # Invalidate LRU cache entry immediately
        _revocation_cache.pop(jti, None)
        logger.info("Revoked token jti=%s for user=%s", jti, claims.sub)
    except Exception as exc:
        logger.error("Failed to revoke token jti=%s: %s", jti, exc)
        raise HTTPException(status_code=500, detail="Logout failed")

    return {"detail": "Logged out"}
