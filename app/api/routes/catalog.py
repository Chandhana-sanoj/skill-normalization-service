"""API route for retrieving the canonical skill catalogue with search, filtering, and pagination."""

from fastapi import APIRouter, Depends, Query, Request

from app.api.routes.auth import get_current_user

router = APIRouter(
    prefix="/api/v1/catalog",
    tags=["Catalog"],
)


@router.get("")
def get_catalog(
    request: Request,
    current_user=Depends(get_current_user),
    q: str = Query(default="", alias="q"),
    category: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=10000),
):
    """Return the canonical skill catalogue with optional search, category filter, and pagination."""
    canonical_map = request.app.state.canonical_map
    description_map = request.app.state.description_map
    category_map = request.app.state.category_map

    # Build the full list of canonical skills.
    all_skills = [
        {
            "id": skill_id,
            "normalizedSkill": skill_name,
            "description": description_map.get(skill_id, "") or "",
            "category": category_map.get(skill_id, "") or "",
        }
        for skill_id, skill_name in canonical_map.items()
    ]

    # Collect distinct category values (non-empty) for the filter dropdown.
    categories = sorted(
        {s["category"] for s in all_skills if s["category"]}
    )

    # Apply text search (case-insensitive, matches skill name or description).
    search_lower = q.strip().lower() if q else ""
    if search_lower:
        all_skills = [
            s
            for s in all_skills
            if search_lower in s["normalizedSkill"].lower()
            or search_lower in s["description"].lower()
        ]

    # Apply category filter.
    if category:
        all_skills = [s for s in all_skills if s["category"] == category]

    total = len(all_skills)

    # Apply pagination.
    offset = (page - 1) * limit
    page_skills = all_skills[offset : offset + limit]

    return {
        "items": page_skills,
        "total": total,
        "page": page,
        "limit": limit,
        "categories": categories,
    }
