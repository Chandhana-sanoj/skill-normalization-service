"""API route for normalizing one or more skills from an input string."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.schemas.normalization_schema import (
    NormalizationRequest,
    NormalizationResponse,
)
from app.core.security import get_current_user
from app.services.multi_skill_extractor import MultiSkillExtractor
from app.services.normalizer import SkillNormalizer

router = APIRouter(prefix="/api/v1", tags=["Normalization"])

_logger = logging.getLogger(__name__)


@router.post("/normalize", response_model=list[NormalizationResponse])
def normalize_skill(
    payload: NormalizationRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Extract skills from the input, then normalize each candidate."""
    app_state = request.app.state

    try:
        extractor = MultiSkillExtractor(
            alias_map=app_state.alias_map,
            canonical_map=app_state.canonical_map,
        )

        candidates = extractor.extract_detailed(payload.input)

        normalizer = SkillNormalizer(
            alias_map=app_state.alias_map,
            canonical_map=app_state.canonical_map,
            vector_searcher=app_state.vector_searcher,
            organization_id=current_user["organization_id"],
            description_map=app_state.description_map,
            category_map=app_state.category_map,
        )

        results = [
            normalizer.normalize(
                candidate.text,
                version=candidate.version,
            )
            for candidate in candidates
        ]

        # Persist normalization results to history (best-effort; never raises).
        try:
            from app.repositories.normalization_history_repository import (  # noqa: PLC0415
                NormalizationHistoryRepository,
            )

            hist_repo = NormalizationHistoryRepository()
            hist_repo.save_batch(current_user["organization_id"], results)
        except Exception as exc:  # pylint: disable=broad-except
            _logger.warning("Failed to persist normalization history: %s", exc)

        return results

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
