
"""Organization user management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from psycopg import errors
from pwdlib import PasswordHash

from app.core.security import get_current_user
from app.repositories.organization_user_repository import (
    OrganizationUserRepository,
)
from app.repositories.organization_repository import (
    OrganizationRepository,
)

router = APIRouter(
    prefix="/api/v1/organizations/me/users",
    tags=["Organization Users"],
)

password_hash = PasswordHash.recommended()


class CreateUserRequest(BaseModel):
    username: str = Field(
        ..., min_length=3, max_length=50,
        pattern=r"^[a-zA-Z0-9_.-]+$",
    )
    password: str = Field(..., min_length=8, max_length=128)


def require_admin(current_user: dict) -> None:
    if current_user.get("role") != "org_admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can manage users",
        )


@router.get("")
def list_users(
    current_user: dict = Depends(get_current_user),
):
    require_admin(current_user)

    users = OrganizationRepository().list_by_organization(
        current_user["organization_id"]
    )

    return {"items": users, "total": len(users)}


@router.post("", status_code=201)
def create_user(
    payload: CreateUserRequest,
    current_user: dict = Depends(get_current_user),
):
    require_admin(current_user)

    try:
        user_id = OrganizationUserRepository().create(
            organization_id=current_user["organization_id"],
            username=payload.username,
            password_hash=password_hash.hash(payload.password),
            role="org_user",
        )
    except errors.UniqueViolation as exc:
        raise HTTPException(
            status_code=409,
            detail="This username is already registered",
        ) from exc

    return {
        "id": user_id,
        "organization_id": current_user["organization_id"],
        "username": payload.username.strip(),
        "role": "org_user",
        "message": "User created successfully",
    }


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user: dict = Depends(get_current_user),
):
    require_admin(current_user)

    if user_id == current_user["user_id"]:
        raise HTTPException(
            status_code=400,
            detail="You cannot delete your own account here",
        )

    deleted = OrganizationRepository().delete_by_id(
        organization_id=current_user["organization_id"],
        user_id=user_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="User not found, or the account cannot be deleted",
        )

    return {"message": "User deleted successfully"}
