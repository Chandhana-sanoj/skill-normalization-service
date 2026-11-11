

from pydantic import BaseModel, Field


class OrganizationRegisterRequest(BaseModel):
    organization_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_.-]+$",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )


class OrganizationRegisterResponse(BaseModel):
    organization_id: int
    user_id: int
    organization_name: str
    username: str
    message: str

class LoginRequest(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UnifiedLoginResponse(BaseModel):
    """
    Response from the unified login endpoint.

    ``user_type`` identifies the authenticated account type so the frontend
    can route the user to the correct dashboard without inspecting the JWT.

    Possible values:
    - ``"super_admin"``  — a Super Admin account
    - ``"org_admin"``    — an Organisation Admin (role == org_admin in organization_user)
    - ``"org_user"``     — a regular Organisation User
    """

    access_token: str
    token_type: str = "bearer"
    user_type: str  # "super_admin" | "org_admin" | "org_user"
