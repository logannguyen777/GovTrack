"""backend/src/api/auth_login.py -- Login endpoint."""
import hashlib

from fastapi import APIRouter, HTTPException

from ..auth import create_access_token
from ..database import pg_connection
from ..models.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    """Authenticate and return JWT. SHA256 password check."""
    pw_hash = hashlib.sha256(body.password.encode()).hexdigest()

    async with pg_connection() as conn:
        row = await conn.fetchrow(
            "SELECT id, username, full_name, role, clearance_level, departments "
            "FROM users WHERE username = $1 AND password_hash = $2 AND is_active = TRUE",
            body.username, pw_hash,
        )

    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

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
    )
