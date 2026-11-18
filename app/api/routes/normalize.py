"""API route for normalizing one or more skills from an input string."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.schemas.normalization_schema import (
    NormalizationRequest,
    NormalizationResponse,
    MultiNormalizationRequest,
    MultiNormalizationItem,
    MultiNormalizationResponse,
)

from app.core.security import get_current_user
from app.services.multi_skill_extractor import MultiSkillExtractor
from app.services.normalizer import SkillNormalizer
from app.repositories.organization_input_mapping_repository import (
    OrganizationInputMappingRepository,
)

router = APIRouter(prefix="/api/v1", tags=["Normalization"])

_logger = logging.getLogger(__name__)


def _load_org_input_mappings(organization_id: int) -> dict[str, int]:
    """Load org-specific input mappings best-effort; return empty dict on error."""
    try:
        repo = OrganizationInputMappingRepository()
        return repo.load_for_organization(organization_id)
    except Exception as exc:  # pylint: disable=broad-except
        _logger.warning(
            "Could not load org input mappings for org %s: %s", organization_id, exc
        )
        return {}


def _build_normalizer(app_state, organization_id: int, org_input_mappings: dict) -> SkillNormalizer:
    """Construct a SkillNormalizer with all app-state data."""
    aliases_by_canonical = getattr(app_state, "aliases_by_canonical", {})
    return SkillNormalizer(
        alias_map=app_state.alias_map,
        canonical_map=app_state.canonical_map,
        vector_searcher=app_state.vector_searcher,
        organization_id=organization_id,
        description_map=app_state.description_map,
        category_map=app_state.category_map,
        aliases_by_canonical=aliases_by_canonical,
        org_input_mappings=org_input_mappings,
    )


def _enrich_with_aliases(result: dict, app_state) -> None:
    """Add aliases list to a matched result in-place; unresolved gets []."""
    if result.get("status") == "matched" and result.get("skill"):
        canonical_name = result["skill"]
        canonical_id = next(
            (cid for cid, name in app_state.canonical_map.items() if name == canonical_name),
            None,
        )
        aliases_by_canonical = getattr(app_state, "aliases_by_canonical", {})
        result["aliases"] = (
            aliases_by_canonical.get(canonical_id, []) if canonical_id is not None else []
        )
    else:
        result["aliases"] = []


@router.post("/normalize", response_model=list[NormalizationResponse])
def normalize_skill(
    payload: NormalizationRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Extract skills from the input, then normalize each candidate."""
    app_state = request.app.state
    organization_id = current_user["organization_id"]

    # Load org-specific input→canonical mappings (admin-confirmed duplicates).
    org_input_mappings = _load_org_input_mappings(organization_id)

    try:
        extractor = MultiSkillExtractor(
            alias_map=app_state.alias_map,
            canonical_map=app_state.canonical_map,
        )

        candidates = extractor.extract_detailed(payload.input)

        normalizer = _build_normalizer(app_state, organization_id, org_input_mappings)

        results = [
            normalizer.normalize(
                candidate.text,
                version=candidate.version,
            )
            for candidate in candidates
        ]

        for result in results:
            _enrich_with_aliases(result, app_state)

        # Persist normalization results to history (best-effort; never raises).
        try:
            from app.repositories.normalization_history_repository import (  # noqa: PLC0415
                NormalizationHistoryRepository,
            )

            hist_repo = NormalizationHistoryRepository()
            hist_repo.save_batch(organization_id, results)
        except Exception as exc:  # pylint: disable=broad-except
            _logger.warning("Failed to persist normalization history: %s", exc)

        return results

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@router.post("/normalize/batch", response_model=MultiNormalizationResponse)
def normalize_batch(
    payload: MultiNormalizationRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Normalize up to 500 input strings, preserving their source indexes."""
    app_state = request.app.state
    organization_id = current_user["organization_id"]

    # Load org-specific input→canonical mappings once for the whole batch.
    org_input_mappings = _load_org_input_mappings(organization_id)

    try:
        extractor = MultiSkillExtractor(
            alias_map=app_state.alias_map,
            canonical_map=app_state.canonical_map,
        )

        normalizer = _build_normalizer(app_state, organization_id, org_input_mappings)

        results = []
        response_items = []

        for source_index, input_text in enumerate(payload.inputs):
            candidates = extractor.extract_detailed(input_text)

            for candidate in candidates:
                result = normalizer.normalize(
                    candidate.text,
                    version=candidate.version,
                )

                _enrich_with_aliases(result, app_state)

                results.append(result)
                response_items.append(
                    MultiNormalizationItem(
                        source_index=source_index,
                        result=NormalizationResponse(**result),
                    )
                )

        # Persist the batch to normalization history (best-effort).
        try:
            from app.repositories.normalization_history_repository import (
                NormalizationHistoryRepository,
            )

            hist_repo = NormalizationHistoryRepository()
            hist_repo.save_batch(organization_id, results)
        except Exception as exc:
            _logger.warning(
                "Failed to persist batch normalization history: %s", exc
            )

        return MultiNormalizationResponse(results=response_items)

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
