"""API routes for managing organization-specific skills."""

import psycopg

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from app.core.config import DB_CONFIG
from app.core.security import get_current_user
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.organization_skill_repository import OrganizationSkillRepository


def require_org_admin(current_user: dict) -> None:
    if current_user.get("role") != "org_admin":
        raise HTTPException(
            status_code=403,
            detail="Only organization admins can perform this action",
        )


router = APIRouter(
    prefix="/api/v1/organizations",
    tags=["Organizations"],
)


# ── Request schemas ───────────────────────────────────────────────────────────

class OrganizationSkillRequest(BaseModel):
    raw_skill:        str        = Field(..., min_length=1, max_length=300)
    normalized_skill: str        = Field(..., min_length=1, max_length=300)
    category:         str | None = Field(default=None, max_length=150)
    description:      str | None = Field(default=None, max_length=2000)


class PromoteUnresolvedRequest(BaseModel):
    raw_skill:        str        = Field(..., min_length=1, max_length=300)
    normalized_skill: str        = Field(..., min_length=1, max_length=300)
    category:         str | None = Field(default=None, max_length=150)
    description:      str | None = Field(default=None, max_length=2000)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_categories(request: Request) -> list[str]:
    """Return sorted distinct categories from the in-memory catalogue."""
    category_map: dict = request.app.state.category_map
    return sorted({v for v in category_map.values() if v})


def _validate_fields(raw_skill: str, normalized_skill: str) -> None:
    if not raw_skill:
        raise HTTPException(status_code=422, detail="Raw skill cannot be empty")
    if not normalized_skill:
        raise HTTPException(status_code=422, detail="Normalized skill cannot be empty")


def _make_embedding(request: Request, normalized_skill: str) -> list[float]:
    return request.app.state.vector_searcher.model.encode(
        normalized_skill,
        normalize_embeddings=True,
    ).tolist()


def _skill_response(skill_id: int, organization_id: int, payload, message: str) -> dict:
    return {
        "id":              skill_id,
        "organization_id": organization_id,
        "rawSkill":        payload.raw_skill.strip(),
        "normalizedSkill": payload.normalized_skill.strip(),
        "category":        payload.category or "",
        "description":     payload.description or "",
        "message":         message,
    }


# ── Catalogue categories (for form dropdown) ──────────────────────────────────

@router.get("/me/categories")
def get_org_skill_categories(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Return distinct categories from the canonical catalogue.

    The frontend populates its category dropdown exclusively from this list.
    Users cannot introduce custom categories through the skill form.
    """
    return {"categories": _get_categories(request)}


# ── List skills ───────────────────────────────────────────────────────────────

@router.get("/me/skills")
def get_my_organization_skills(
    current_user: dict = Depends(get_current_user),
    q:     str = Query(default="", alias="q"),
    page:  int = Query(default=1,  ge=1),
    limit: int = Query(default=25, ge=1, le=200),
):
    """Return paginated organization skills for the authenticated user's org."""
    organization_id = current_user["organization_id"]

    if not OrganizationRepository().exists(organization_id):
        raise HTTPException(status_code=404, detail="Organization not found")

    items, total = OrganizationSkillRepository().list_by_organization(
        organization_id=organization_id,
        search=q,
        page=page,
        limit=limit,
    )

    return {
        "organization_id": organization_id,
        "items":  items,
        "total":  total,
        "page":   page,
        "limit":  limit,
    }


# ── Create skill ──────────────────────────────────────────────────────────────

@router.post("/me/skills", status_code=201)
def create_organization_skill(
    payload: OrganizationSkillRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    require_org_admin(current_user)
    organization_id = current_user["organization_id"]

    raw_skill        = payload.raw_skill.strip()
    normalized_skill = payload.normalized_skill.strip()
    _validate_fields(raw_skill, normalized_skill)

    repo = OrganizationSkillRepository()

    if repo.find_by_name(organization_id, normalized_skill):
        raise HTTPException(
            status_code=409,
            detail="A skill with this normalized name already exists in your organization",
        )

    embedding = _make_embedding(request, normalized_skill)

    skill_id = repo.create(
        organization_id=organization_id,
        raw_skill=raw_skill,
        normalized_skill=normalized_skill,
        category=payload.category or None,
        description=payload.description or None,
        embedding=embedding,
    )

    return _skill_response(skill_id, organization_id, payload, "Skill created successfully")


# ── Update skill ──────────────────────────────────────────────────────────────

@router.put("/me/skills/{skill_id}")
def update_organization_skill(
    skill_id: int,
    payload: OrganizationSkillRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    require_org_admin(current_user)
    organization_id = current_user["organization_id"]

    raw_skill        = payload.raw_skill.strip()
    normalized_skill = payload.normalized_skill.strip()
    _validate_fields(raw_skill, normalized_skill)

    repo = OrganizationSkillRepository()

    # Duplicate check: another record (not this one) with the same name.
    duplicate = repo.find_by_name(organization_id, normalized_skill, exclude_id=skill_id)
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="Another skill with this normalized name already exists",
        )

    embedding = _make_embedding(request, normalized_skill)

    updated = repo.update(
        organization_id=organization_id,
        skill_id=skill_id,
        raw_skill=raw_skill,
        normalized_skill=normalized_skill,
        category=payload.category or None,
        description=payload.description or None,
        embedding=embedding,
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Skill not found in your organization")

    return _skill_response(skill_id, organization_id, payload, "Skill updated successfully")


# ── Delete skill ──────────────────────────────────────────────────────────────

@router.delete("/me/skills/{skill_id}", status_code=204)
def delete_organization_skill(
    skill_id: int,
    current_user: dict = Depends(get_current_user),
):
    require_org_admin(current_user)
    organization_id = current_user["organization_id"]

    deleted = OrganizationSkillRepository().delete(
        organization_id=organization_id,
        skill_id=skill_id,
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="Skill not found in your organization")

    return Response(status_code=204)


# ── Promote unresolved → org skill (single transaction) ──────────────────────

@router.post("/me/unresolved/{unresolved_id}/promote", status_code=201)
def promote_unresolved_to_org_skill(
    unresolved_id: int,
    payload: PromoteUnresolvedRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Atomically create an org skill and delete the unresolved record.

    Both writes execute on the same psycopg connection so they share one
    transaction.  If the INSERT fails the DELETE never happens; if anything
    fails after the INSERT the whole transaction is rolled back and the
    unresolved record is preserved.

    A 409 is returned (without touching the DB) when a duplicate org skill
    already exists.
    """
    require_org_admin(current_user)
    organization_id = current_user["organization_id"]

    raw_skill        = payload.raw_skill.strip()
    normalized_skill = payload.normalized_skill.strip()
    _validate_fields(raw_skill, normalized_skill)

    repo = OrganizationSkillRepository()

    # Pre-flight duplicate check (outside the transaction for a clear message).
    if repo.find_by_name(organization_id, normalized_skill):
        raise HTTPException(
            status_code=409,
            detail="A skill with this normalized name already exists in your organization",
        )

    embedding = _make_embedding(request, normalized_skill)

    # ── Single transaction ────────────────────────────────────────────────────
    with psycopg.connect(**DB_CONFIG) as conn:

        # 1. Verify the unresolved record belongs to this org.
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM unresolved_skill WHERE id = %s AND organization_id = %s;",
                (unresolved_id, organization_id),
            )
            if cur.fetchone() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Unresolved skill not found in your organization",
                )

        # 2. Insert the org skill.
        skill_id = repo.create_in_transaction(
            conn=conn,
            organization_id=organization_id,
            raw_skill=raw_skill,
            normalized_skill=normalized_skill,
            category=payload.category or None,
            description=payload.description or None,
            embedding=embedding,
        )

        # 3. Delete the unresolved record.
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM unresolved_skill WHERE id = %s AND organization_id = %s;",
                (unresolved_id, organization_id),
            )

        conn.commit()
    # ── End transaction ───────────────────────────────────────────────────────

    return {
        "id":              skill_id,
        "organization_id": organization_id,
        "rawSkill":        raw_skill,
        "normalizedSkill": normalized_skill,
        "category":        payload.category or "",
        "description":     payload.description or "",
        "message": (
            "Skill added to your organization and removed from the unresolved queue."
        ),
    }
