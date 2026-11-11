import os
import jwt

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.repositories.super_admin_repository import SuperAdminRepository

security = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"


def get_current_super_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )

        if payload.get("type") != "super_admin":
            raise HTTPException(
                status_code=403,
                detail="Super Admin access required",
            )

        admin_id = int(payload.get("sub"))

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid admin ID",
        )

    admin = SuperAdminRepository().find_by_id(admin_id)

    if admin is None or not admin["is_active"]:
        raise HTTPException(
            status_code=401,
            detail="Super Admin account is inactive",
        )

    return {
        "admin_id": admin["id"],
        "username": admin["username"],
    }