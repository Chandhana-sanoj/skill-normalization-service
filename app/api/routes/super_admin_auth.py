
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException
from pwdlib import PasswordHash

from app.api.schemas.auth_schema import LoginRequest, LoginResponse
from app.repositories.super_admin_repository import SuperAdminRepository


router = APIRouter(
    prefix="/api/v1/super-admin/auth",
    tags=["Super Admin Authentication"],
)

password_hash = PasswordHash.recommended()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_HOURS = 8


@router.post("/login", response_model=LoginResponse)
def super_admin_login(payload: LoginRequest):

    if not JWT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="JWT_SECRET is not configured",
        )

    repository = SuperAdminRepository()
    admin = repository.find_by_username(payload.username)

    if (
        admin is None
        or not admin["is_active"]
        or not password_hash.verify(
            payload.password,
            admin["password_hash"],
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    now = datetime.now(timezone.utc)

    token_payload = {
        "sub": str(admin["id"]),
        "username": admin["username"],
        "type": "super_admin",
        "iat": now,
        "exp": now + timedelta(hours=ACCESS_TOKEN_HOURS),
    }

    access_token = jwt.encode(
        token_payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    repository.update_last_login(admin["id"])

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
