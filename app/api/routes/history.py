"""API route for retrieving normalization history (paginated)."""

from fastapi import APIRouter, Depends, Query

from app.core.security import get_current_user
from app.repositories.normalization_history_repository import (
    NormalizationHistoryRepository,
)

router = APIRouter(prefix="/api/v1/organizations", tags=["Normalization History"])


@router.get("/me/history")
def list_normalization_history(
    current_user: dict = Depends(get_current_user),
    q: str = Query(default="", alias="q"),
    status: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=200),
):
    """Return paginated normalization history for the authenticated organization."""
    organization_id = current_user["organization_id"]

    repository = NormalizationHistoryRepository()
    items, total = repository.list_by_organization(
        organization_id=organization_id,
        search=q,
        status=status,
        page=page,
        limit=limit,
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
    }
