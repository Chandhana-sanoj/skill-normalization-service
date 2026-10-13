
from pydantic import BaseModel, Field


class NormalizationRequest(BaseModel):
    input: str = Field(
        ...,
        min_length=1,
        description="Skill name or text to normalize",
        examples=["Python 3.12"],
    )
    organization_id: int = Field(
        ...,
        gt=0,
        description="ID of the organization requesting normalization",
    )


class NormalizationResponse(BaseModel):
    input: str
    skill: str | None
    version: str | None
    description: str | None
    status: str
