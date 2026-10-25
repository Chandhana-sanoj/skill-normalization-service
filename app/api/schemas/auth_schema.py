

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
