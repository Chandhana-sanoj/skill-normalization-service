
import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends
from app.core.security import get_current_user

import jwt
from fastapi import APIRouter, HTTPException
from psycopg import errors
from pwdlib import PasswordHash

from app.api.schemas.auth_schema import (
    LoginRequest,
    LoginResponse,
    OrganizationRegisterRequest,
    OrganizationRegisterResponse,
)
from app.repositories.organization_repository import (
    OrganizationRepository,
)
from app.repositories.organization_user_repository import (
    OrganizationUserRepository,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

password_hash = PasswordHash.recommended()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 30


@router.post(
    "/register",
    response_model=OrganizationRegisterResponse,
    status_code=201,
)
def register_organization(
    payload: OrganizationRegisterRequest,
):
    hashed_password = password_hash.hash(payload.password)
    repository = OrganizationRepository()

    try:
        result = repository.create_with_admin(
            organization_name=payload.organization_name,
            username=payload.username,
            password_hash=hashed_password,
        )
    except errors.UniqueViolation as exc:
        raise HTTPException(
            status_code=409,
            detail="This username is already registered",
        ) from exc

    return {
        **result,
        "message": "Organization registered successfully",
    }


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    if not JWT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="JWT_SECRET is not configured",
        )

    repository = OrganizationUserRepository()
    user = repository.find_by_username(payload.username)

    if user is None or not password_hash.verify(
        payload.password,
        user["password_hash"],
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    now = datetime.now(timezone.utc)
    token_payload = {
        "sub": str(user["id"]),
        "organization_id": user["organization_id"],
        "username": user["username"],
        "role": user["role"],
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
    }

    access_token = jwt.encode(
        token_payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/me")
def get_logged_in_user(
    current_user: dict = Depends(get_current_user),
):
    """Return the authenticated user's profile, including their organization name."""
    import psycopg
    from app.core.config import DB_CONFIG

    organization_name = "Your organization"
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT name FROM organization WHERE id = %s;",
                    (current_user["organization_id"],),
                )
                row = cur.fetchone()
                if row:
                    organization_name = row[0]
    except Exception:  # pylint: disable=broad-except
        pass  # Fall back to placeholder; do not break login

    return {
        **current_user,
        "organization_name": organization_name,
    }
