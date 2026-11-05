"""API route for retrieving normalization history (paginated)."""

from fastapi import APIRouter, Depends, Query, Request

from app.core.security import get_current_user
from app.repositories.normalization_history_repository import (
    NormalizationHistoryRepository,
)

router = APIRouter(prefix="/api/v1/organizations", tags=["Normalization History"])


@router.get("/me/history")
def list_normalization_history(
    request: Request,
    current_user: dict = Depends(get_current_user),
    q: str = Query(default="", alias="q"),
    status: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=200),
):
    """Return paginated normalization history for the authenticated organization."""
    organization_id = current_user["organization_id"]
    aliases_by_canonical = getattr(request.app.state, "aliases_by_canonical", {})
    canonical_map = getattr(request.app.state, "canonical_map", {})

    repository = NormalizationHistoryRepository()
    items, total = repository.list_by_organization(
        organization_id=organization_id,
        search=q,
        status=status,
        page=page,
        limit=limit,
    )

    # Enrich matched history items with their canonical skill's aliases.
    # Unresolved items (no normalizedSkill) receive an empty list.
    for item in items:
        normalized_skill = item.get("normalizedSkill")
        if item.get("status") == "matched" and normalized_skill:
            canonical_id = next(
                (cid for cid, name in canonical_map.items() if name == normalized_skill),
                None,
            )
            item["aliases"] = aliases_by_canonical.get(canonical_id, []) if canonical_id is not None else []
        else:
            item["aliases"] = []

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
    }
