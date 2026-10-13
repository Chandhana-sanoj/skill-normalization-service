
from fastapi import APIRouter, HTTPException, Request

from app.api.schemas.normalization_schema import (
    NormalizationRequest,
    NormalizationResponse,
)

router = APIRouter(prefix="/api/v1", tags=["Normalization"])


@router.post("/normalize", response_model=NormalizationResponse)
def normalize_skill(
    payload: NormalizationRequest,
    request: Request,
):
    normalizer = request.app.state.normalizer

    try:
        return normalizer.normalize(payload.input)

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

