"""API routes for listing and resolving unresolved skills (admin only)."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from app.core.security import get_current_user
from app.repositories.unresolved_skill_repository import UnresolvedSkillRepository

import psycopg
from psycopg.types.json import Jsonb

from app.repositories.canonical_skill_repository import (
    CanonicalSkillRepository,
)

from fastapi import Request

from app.core.config import DB_CONFIG
from app.repositories.organization_skill_repository import (
    OrganizationSkillRepository,
)
from app.repositories.organization_input_mapping_repository import (
    OrganizationInputMappingRepository,
)

def require_org_admin(current_user: dict) -> None:
    if current_user.get("role") != "org_admin":
        raise HTTPException(
            status_code=403,
            detail="Only organization admins can manage unresolved skills",
        )


router = APIRouter(
    prefix="/api/v1/organizations",
    tags=["Unresolved Skills"],
)


class ResolveRequest(BaseModel):
    """Body for resolving an unresolved skill record.

    The frontend sends the corrected skill name and optional notes; we store
    resolution by simply deleting the unresolved record. The caller is
    expected to add the resolved skill to their organization skills if needed.
    """
    normalized_skill: str | None = None
    category: str | None = None
    notes: str | None = None


class UpdateUnresolvedRequest(BaseModel):
    """Body for updating the raw input text of an unresolved skill record."""
    input: str

class ApproveSuggestionRequest(BaseModel):
    canonical_skill_id: int | None = None
    name: str | None = None
    description: str | None = None
    category: str | None = None
    aliases: list[str] | None = None


@router.get("/me/unresolved")
def list_unresolved_skills(
    current_user: dict = Depends(get_current_user),
    q: str = Query(default="", alias="q"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=200),
):
    """Return paginated unresolved skills for the authenticated organization (admin only)."""
    require_org_admin(current_user)
    organization_id = current_user["organization_id"]

    repository = UnresolvedSkillRepository()
    items, total = repository.list_by_organization(
        organization_id=organization_id,
        search=q,
        page=page,
        limit=limit,
    )

    return {
        "organization_id": organization_id,
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.post("/me/unresolved/{unresolved_id}/resolve", status_code=200)
def resolve_unresolved_skill(
    unresolved_id: int,
    payload: ResolveRequest,
    current_user: dict = Depends(get_current_user),
):
    """Mark an unresolved skill as resolved (admin only).

    This removes the record from the unresolved queue. The admin is expected
    to have manually added the skill to their organization skills if they wish
    to retain it.
    """
    require_org_admin(current_user)
    organization_id = current_user["organization_id"]

    repository = UnresolvedSkillRepository()
    deleted = repository.resolve(
        organization_id=organization_id,
        unresolved_id=unresolved_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Unresolved skill not found in your organization",
        )

    return {"message": "Skill resolved and removed from the unresolved queue"}


@router.put("/me/unresolved/{unresolved_id}", status_code=200)
def update_unresolved_skill(
    unresolved_id: int,
    payload: UpdateUnresolvedRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update the raw input text of an unresolved skill record (admin only)."""
    require_org_admin(current_user)
    organization_id = current_user["organization_id"]

    new_input = payload.input.strip()
    if not new_input:
        raise HTTPException(
            status_code=422,
            detail="Input text must not be empty",
        )

    repository = UnresolvedSkillRepository()

    # Duplicate check: another record in the same org with the same input text.
    duplicate = repository.find_by_input(
        organization_id=organization_id,
        input_text=new_input,
        exclude_id=unresolved_id,
    )
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="Another unresolved record with the same input text already exists",
        )

    updated = repository.update(
        organization_id=organization_id,
        unresolved_id=unresolved_id,
        new_input=new_input,
    )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Unresolved skill not found in your organization",
        )

    return {"message": "Unresolved skill updated successfully"}


@router.delete("/me/unresolved/{unresolved_id}", status_code=204)
def delete_unresolved_skill(
    unresolved_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Permanently delete an unresolved skill record (admin only)."""
    require_org_admin(current_user)
    organization_id = current_user["organization_id"]

    repository = UnresolvedSkillRepository()
    deleted = repository.delete(
        organization_id=organization_id,
        unresolved_id=unresolved_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Unresolved skill not found in your organization",
        )

    return Response(status_code=204)


@router.post("/me/unresolved/{unresolved_id}/approve", status_code=201)
def approve_unresolved_skill(
    unresolved_id: int,
    payload: ApproveSuggestionRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Approve an LLM suggestion or map to an existing canonical skill.

    Two distinct code paths:

    1. **Duplicate path** (``has_duplicates=True``, ``canonical_skill_id`` provided):
       - Saves an org-scoped input → canonical mapping in
         ``organization_input_mapping``.
       - Records the resolution in ``normalization_history`` as a matched entry.
       - Deletes the ``unresolved_skill`` record.
       - Does NOT create an ``organization_skill`` record.

    2. **Normal approval path** (``has_duplicates=False``):
       - Preserves the existing behaviour: creates an ``organization_skill``
         record from the LLM suggestion (optionally edited by the admin).
    """
    require_org_admin(current_user)

    organization_id = current_user["organization_id"]
    skill_repository = OrganizationSkillRepository()
    canonical_repository = CanonicalSkillRepository()
    mapping_repository = OrganizationInputMappingRepository()

    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT input, suggestion
                    FROM unresolved_skill
                    WHERE id = %s AND organization_id = %s
                    FOR UPDATE;
                    """,
                    (unresolved_id, organization_id),
                )

                row = cur.fetchone()

                if not row:
                    raise HTTPException(
                        status_code=404,
                        detail="Unresolved skill not found.",
                    )

                raw_skill, suggestion = row

                if not suggestion:
                    raise HTTPException(
                        status_code=400,
                        detail="No LLM suggestion available for this skill.",
                    )

                duplicate_check = suggestion.get("duplicate_check") or {}
                has_duplicates = duplicate_check.get("has_duplicates", False)

                # ── Duplicate path ───────────────────────────────────────────
                # Map the original input to the selected canonical skill.
                # Never creates an organization_skill record.
                if has_duplicates:
                    if payload.canonical_skill_id is None:
                        raise HTTPException(
                            status_code=409,
                            detail={
                                "message": "A matching canonical skill must be selected.",
                                "duplicate_check": duplicate_check,
                            },
                        )

                    matched_ids = {
                        int(skill_id)
                        for skill_id in duplicate_check.get(
                            "matched_canonical_ids", []
                        )
                    }

                    if payload.canonical_skill_id not in matched_ids:
                        raise HTTPException(
                            status_code=422,
                            detail="Selected skill is not among the detected matches.",
                        )

                    canonical_skill = canonical_repository.get_skill_by_id(
                        payload.canonical_skill_id
                    )

                    if not canonical_skill:
                        raise HTTPException(
                            status_code=404,
                            detail="Selected canonical skill no longer exists.",
                        )

                    canonical_name = canonical_skill["name"]
                    canonical_description = canonical_skill.get("description")
                    canonical_category = canonical_skill.get("category")

                    # 1. Save the org-scoped input → canonical mapping.
                    mapping_repository.save_in_transaction(
                        conn=conn,
                        organization_id=organization_id,
                        raw_input=raw_skill,
                        canonical_skill_id=payload.canonical_skill_id,
                    )

                    # 2. Record the resolution in normalization history so it
                    #    appears in the Normalization Output page immediately.
                    cur.execute(
                        """
                        INSERT INTO normalization_history (
                            organization_id,
                            input_skill,
                            normalized_skill,
                            version,
                            description,
                            category,
                            status
                        )
                        VALUES (%s, %s, %s, NULL, %s, %s, 'matched')
                        ON CONFLICT DO NOTHING;
                        """,
                        (
                            organization_id,
                            raw_skill,
                            canonical_name,
                            canonical_description,
                            canonical_category,
                        ),
                    )

                    # 3. Delete the unresolved record only after both inserts
                    #    succeed (they are in the same transaction).
                    cur.execute(
                        """
                        DELETE FROM unresolved_skill
                        WHERE id = %s AND organization_id = %s;
                        """,
                        (unresolved_id, organization_id),
                    )

                    return {
                        "message": "Input mapped to existing canonical skill.",
                        "mapping": "organization_input_mapping",
                        "raw_skill": raw_skill,
                        "canonical_skill_id": payload.canonical_skill_id,
                        "canonical_name": canonical_name,
                    }

                # ── Normal approval path ─────────────────────────────────────
                # LLM suggestion approved (possibly edited).
                # Creates an organization_skill record as before.
                else:
                    if payload.canonical_skill_id is not None:
                        raise HTTPException(
                            status_code=422,
                            detail="No duplicate canonical skill is available for selection.",
                        )

                    # Preserve the existing suggestion approval behaviour.
                    name = (payload.name or suggestion.get("name", "")).strip()

                    description = (
                        payload.description
                        if payload.description is not None
                        else suggestion.get("description")
                    )

                    category = (
                        payload.category
                        if payload.category is not None
                        else suggestion.get("category")
                    )

                    aliases = (
                        payload.aliases
                        if payload.aliases is not None
                        else suggestion.get("aliases", [])
                    )

                    if not name:
                        raise HTTPException(
                            status_code=422,
                            detail="Skill name cannot be empty.",
                        )

                    if not isinstance(aliases, list):
                        raise HTTPException(
                            status_code=422,
                            detail="Aliases must be a list.",
                        )

                    # Prevent duplicate organization skills.
                    cur.execute(
                        """
                        SELECT id
                        FROM organization_skill
                        WHERE organization_id = %s
                          AND LOWER(COALESCE(normalized_skill, name)) = LOWER(%s)
                        LIMIT 1;
                        """,
                        (organization_id, name),
                    )

                    if cur.fetchone():
                        raise HTTPException(
                            status_code=409,
                            detail="This skill already exists in organization skills.",
                        )

                    # Reuse the application-level embedding model.
                    embedding = request.app.state.vector_searcher.make_embedding(name)

                    skill_id = skill_repository.create_in_transaction(
                        conn=conn,
                        organization_id=organization_id,
                        raw_skill=raw_skill,
                        normalized_skill=name,
                        category=category,
                        description=description,
                        embedding=embedding,
                    )

                    skill_repository.add_aliases_in_transaction(
                        conn=conn,
                        organization_skill_id=skill_id,
                        aliases=aliases,
                    )

                    # Delete unresolved record only after successful insertion.
                    cur.execute(
                        """
                        DELETE FROM unresolved_skill
                        WHERE id = %s AND organization_id = %s;
                        """,
                        (unresolved_id, organization_id),
                    )

                return {
                    "message": "Skill approved successfully.",
                    "organization_skill_id": skill_id,
                    "name": name,
                    "aliases": aliases,
                    "selected_canonical_skill_id": payload.canonical_skill_id,
                }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to approve skill. No changes were committed.",
        ) from exc
