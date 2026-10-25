from pydantic import BaseModel, Field


class NormalizationRequest(BaseModel):
    input: str = Field(
        ...,
        min_length=1,
        description="Skill name or text to normalize",
        examples=["Python 3.12"],
    )


class NormalizationResponse(BaseModel):
    input: str
    skill: str | None
    version: str | None
    description: str | None
    category: str | None
    status: str


class MultiNormalizationRequest(BaseModel):
    inputs: list[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of skill phrases to normalize",
        examples=[["Python for Machine Learning", "Java 17"]],
    )


class MultiNormalizationItem(BaseModel):
    source_index: int
    result: NormalizationResponse


class MultiNormalizationResponse(BaseModel):
    results: list[MultiNormalizationItem]
