"""API routes for listing and resolving unresolved skills (admin only)."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from app.core.security import get_current_user
from app.repositories.unresolved_skill_repository import UnresolvedSkillRepository


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
