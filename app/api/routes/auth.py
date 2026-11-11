
import logging
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
    UnifiedLoginResponse,
)
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.organization_user_repository import OrganizationUserRepository
from app.repositories.super_admin_repository import SuperAdminRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

password_hash = PasswordHash.recommended()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 30
SA_ACCESS_TOKEN_HOURS = 8


@router.post(
    "/register",
    response_model=OrganizationRegisterResponse,
    status_code=201,
)
def register_organization(payload: OrganizationRegisterRequest):
    hashed_password = password_hash.hash(payload.password)
    repository = OrganizationRepository()
    try:
        result = repository.create_with_admin(
            organization_name=payload.organization_name,
            username=payload.username,
            password_hash=hashed_password,
        )
    except errors.UniqueViolation as exc:
        raise HTTPException(status_code=409, detail="This username is already registered") from exc
    return {**result, "message": "Organization registered successfully"}


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    if not JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT_SECRET is not configured")
    repository = OrganizationUserRepository()
    user = repository.find_by_username(payload.username)
    if user is None or not password_hash.verify(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    now = datetime.now(timezone.utc)
    token_payload = {
        "sub": str(user["id"]),
        "organization_id": user["organization_id"],
        "username": user["username"],
        "role": user["role"],
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
    }
    access_token = jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/unified-login", response_model=UnifiedLoginResponse)
def unified_login(payload: LoginRequest):
    """
    Single login endpoint for all SkillBase users.

    Diagnostic logging is active. Logs record which authentication step fails
    without ever writing the plaintext password or the stored hash value.

    Authentication priority:
      1. super_admin table — checked first.
      2. organization_user table — checked only if no SA record was found.

    If a username matches a Super Admin record the credential is *never*
    compared against the org-user table, preventing account shadowing.
    """
    if not JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT_SECRET is not configured")

    username = payload.username.strip()
    now = datetime.now(timezone.utc)

    # ── 1. Super Admin lookup ─────────────────────────────────────────────────
    sa_repo = SuperAdminRepository()
    admin = sa_repo.find_by_username(username)

    logger.warning(
        "[unified-login] SA lookup username=%r found=%s",
        username,
        admin is not None,
    )

    if admin is not None:
        is_active = bool(admin.get("is_active"))
        hash_prefix = (admin.get("password_hash") or "")[:12]   # first 12 chars only — safe, reveals algorithm/version not password
        logger.warning(
            "[unified-login] SA record: id=%s is_active=%s hash_prefix=%r",
            admin.get("id"),
            is_active,
            hash_prefix,
        )

        try:
            pw_ok = password_hash.verify(payload.password, admin["password_hash"])
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("[unified-login] verify() raised %s: %s", type(exc).__name__, exc)
            pw_ok = False

        logger.warning(
            "[unified-login] SA password_hash.verify() returned %s",
            pw_ok,
        )

        if not is_active or not pw_ok:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        token_payload = {
            "sub": str(admin["id"]),
            "username": admin["username"],
            "type": "super_admin",
            "iat": now,
            "exp": now + timedelta(hours=SA_ACCESS_TOKEN_HOURS),
        }
        access_token = jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        sa_repo.update_last_login(admin["id"])
        logger.warning("[unified-login] SA login SUCCESS for %r", username)
        return {"access_token": access_token, "token_type": "bearer", "user_type": "super_admin"}

    # ── 2. Organisation user lookup ───────────────────────────────────────────
    org_repo = OrganizationUserRepository()
    user = org_repo.find_by_username(username)

    logger.warning(
        "[unified-login] Org lookup username=%r found=%s",
        username,
        user is not None,
    )

    if user is None or not password_hash.verify(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    raw_role = str(user.get("role") or "").lower()
    user_type = "org_admin" if raw_role in {"org_admin", "admin", "organization_admin"} else "org_user"

    token_payload = {
        "sub": str(user["id"]),
        "organization_id": user["organization_id"],
        "username": user["username"],
        "role": user["role"],
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
    }
    access_token = jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    logger.warning("[unified-login] Org login SUCCESS for %r role=%s", username, user_type)
    return {"access_token": access_token, "token_type": "bearer", "user_type": user_type}


@router.get("/me")
def get_logged_in_user(current_user: dict = Depends(get_current_user)):
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
        pass
    return {**current_user, "organization_name": organization_name}
