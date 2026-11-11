
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from fastapi import Request
from app.core.super_admin_security import get_current_super_admin
from app.repositories.organization_repository import OrganizationRepository

from app.repositories.super_admin_audit_repository import (
    SuperAdminAuditRepository,
)

from app.repositories.organization_user_repository import (
    OrganizationUserRepository,
)

from app.repositories.canonical_skill_repository import (
    CanonicalSkillRepository,
)

from app.repositories.normalization_history_repository import (
    NormalizationHistoryRepository,
)

from app.repositories.unresolved_skill_repository import (
    UnresolvedSkillRepository,
)

from app.repositories.super_admin_dashboard_repository import (
    SuperAdminDashboardRepository,
)

import psycopg
from app.core.config import DB_CONFIG
from app.repositories.organization_skill_repository import OrganizationSkillRepository

router = APIRouter(
    prefix="/api/v1/super-admin",
    tags=["Super Admin"],
    dependencies=[Depends(get_current_super_admin)],
)


class OrganizationStatusRequest(BaseModel):
    is_active: bool

class CreateSkillRequest(BaseModel):
    name: str
    description: str | None = None
    category: str | None = None
class CreateAliasRequest(BaseModel):
    alias: str
class UpdateSkillRequest(BaseModel):
    name: str
    description: str | None = None
    category: str | None = None

@router.get("/organizations")
def get_all_organizations():
    repository = OrganizationRepository()
    organizations = repository.list_all_organizations()

    return {
        "total": len(organizations),
        "organizations": organizations,
    }


@router.patch("/organizations/{organization_id}/status")
def update_organization_status(
    organization_id: int,
    payload: OrganizationStatusRequest,
    admin: dict = Depends(get_current_super_admin),
):
    repository = OrganizationRepository()

    updated = repository.update_organization_status(
        organization_id,
        payload.is_active,
    )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Organization not found or already deleted",
        )

    SuperAdminAuditRepository().create_log(
        super_admin_id=admin["admin_id"],
        action="activate_organization" if payload.is_active
        else "deactivate_organization",
        entity_type="organization",
        entity_id=organization_id,
        details={"is_active": payload.is_active},
    )

    return {"message": "Organization status updated successfully"}


@router.delete("/organizations/{organization_id}")
def delete_organization(
    organization_id: int,
    admin: dict = Depends(get_current_super_admin),
):
    repository = OrganizationRepository()

    deleted = repository.soft_delete_organization(organization_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Organization not found or already deleted",
        )

    SuperAdminAuditRepository().create_log(
        super_admin_id=admin["admin_id"],
        action="delete_organization",
        entity_type="organization",
        entity_id=organization_id,
        details={"deleted": True},
    )

    return {"message": "Organization deleted successfully"}

@router.get("/users")
def get_all_users():
    """Get users across all organizations."""
    repository = OrganizationUserRepository()
    users = repository.list_all_users()

    return {
        "total": len(users),
        "users": users,
    }


@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    payload: OrganizationStatusRequest,
    admin: dict = Depends(get_current_super_admin),
):
    """Activate or deactivate an organization user."""

    repository = OrganizationUserRepository()

    updated = repository.update_user_status(
        user_id=user_id,
        is_active=payload.is_active,
    )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    SuperAdminAuditRepository().create_log(
        super_admin_id=admin["admin_id"],
        action="activate_user" if payload.is_active
        else "deactivate_user",
        entity_type="organization_user",
        entity_id=user_id,
        details={"is_active": payload.is_active},
    )

    return {
        "message": "User status updated successfully"
    }

@router.get("/skills")
def get_all_canonical_skills(
    search: str = "",
    page: int = 1,
    limit: int = 25,
):
    """Get canonical skills with server-side pagination and search."""
    if page < 1 or limit < 1 or limit > 100:
        raise HTTPException(400, "Invalid pagination values")

    repository = CanonicalSkillRepository()
    skills, total = repository.list_paginated(search=search, page=page, limit=limit)

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "skills": skills,
    }


@router.get("/skills/{skill_id}/aliases")
def get_skill_aliases(skill_id: int):
    """Get all aliases for a specific canonical skill."""
    repository = CanonicalSkillRepository()
    aliases = repository.list_aliases(skill_id)
    return {"aliases": aliases}


@router.get("/skills/{skill_id}")
def get_canonical_skill(skill_id: int):
    """Get a single canonical skill with its aliases."""
    repository = CanonicalSkillRepository()
    skill = repository.get_skill_by_id(skill_id)
    if not skill:
        raise HTTPException(404, "Canonical skill not found")
    return skill

@router.post("/skills")
def create_canonical_skill(
    payload: CreateSkillRequest,
    request: Request,
    admin: dict = Depends(get_current_super_admin),
):
    name = payload.name.strip()

    if not name:
        raise HTTPException(400, "Skill name cannot be empty")

    description = payload.description.strip() if payload.description else None
    category = payload.category.strip() if payload.category else None

    repository = CanonicalSkillRepository()

    # Prevent duplicate skill names (efficient lookup)
    existing_check, _ = repository.list_paginated(search=name, page=1, limit=5)
    if any(s["name"].lower() == name.lower() for s in existing_check):
        raise HTTPException(409, "Skill already exists")

    # Generate embedding
    embedding_text = f"{name}. {description}" if description else name
    embedding = request.app.state.vector_searcher.make_embedding(
        embedding_text
    )

    # Save skill
    skill_id = repository.create_skill(
        name=name,
        description=description,
        category=category,
        embedding=embedding,
    )

    # Refresh catalogue cache
    (
        request.app.state.alias_map,
        request.app.state.canonical_map,
        request.app.state.description_map,
        request.app.state.category_map,
        request.app.state.aliases_by_canonical,
    ) = repository.load_catalogue()

    # Record admin action
    SuperAdminAuditRepository().create_log(
        super_admin_id=admin["admin_id"],
        action="create_skill",
        entity_type="canonical_skill",
        entity_id=skill_id,
        details={"name": name, "category": category},
    )

    return {
        "message": "Skill created successfully",
        "skill_id": skill_id,
        "name": name,
    }
@router.post("/skills/{skill_id}/aliases")
def add_skill_alias(
    skill_id: int,
    payload: CreateAliasRequest,
    request: Request,
    admin: dict = Depends(get_current_super_admin),
):
    alias = payload.alias.strip()

    if not alias:
        raise HTTPException(400, "Alias cannot be empty")

    repository = CanonicalSkillRepository()

    # Verify canonical skill exists
    if not repository.get_skill_by_id(skill_id):
        raise HTTPException(404, "Canonical skill not found")
        raise HTTPException(404, "Canonical skill not found")

    # Check for duplicate alias
    existing_aliases = repository.list_aliases(skill_id)

    if any(item["alias"].lower() == alias.lower() for item in existing_aliases):
        raise HTTPException(409, "Alias already exists for this skill")

    alias_id = repository.add_alias(skill_id, alias)

    # Refresh catalogue cache
    (
        request.app.state.alias_map,
        request.app.state.canonical_map,
        request.app.state.description_map,
        request.app.state.category_map,
        request.app.state.aliases_by_canonical,
    ) = repository.load_catalogue()

    SuperAdminAuditRepository().create_log(
        super_admin_id=admin["admin_id"],
        action="add_skill_alias",
        entity_type="skill_alias",
        entity_id=alias_id,
        details={"alias": alias, "canonical_id": skill_id},
    )

    return {
        "message": "Alias added successfully",
        "alias_id": alias_id,
        "alias": alias,
    }


@router.delete("/skills/{skill_id}/aliases/{alias_id}")
def delete_skill_alias(
    skill_id: int,
    alias_id: int,
    request: Request,
    admin: dict = Depends(get_current_super_admin),
):
    repository = CanonicalSkillRepository()

    deleted = repository.delete_alias(alias_id, skill_id)

    if not deleted:
        raise HTTPException(404, "Alias not found for this skill")

    # Refresh catalogue cache
    (
        request.app.state.alias_map,
        request.app.state.canonical_map,
        request.app.state.description_map,
        request.app.state.category_map,
        request.app.state.aliases_by_canonical,
    ) = repository.load_catalogue()

    SuperAdminAuditRepository().create_log(
        super_admin_id=admin["admin_id"],
        action="delete_skill_alias",
        entity_type="skill_alias",
        entity_id=alias_id,
        details={"canonical_id": skill_id},
    )

    return {"message": "Alias deleted successfully"}

@router.put("/skills/{skill_id}")
def update_canonical_skill(
    skill_id: int,
    payload: UpdateSkillRequest,
    request: Request,
    admin: dict = Depends(get_current_super_admin),
):
    name = payload.name.strip()

    if not name:
        raise HTTPException(400, "Skill name cannot be empty")

    description = payload.description.strip() if payload.description else None
    category = payload.category.strip() if payload.category else None

    repository = CanonicalSkillRepository()

    # Verify skill exists
    existing = repository.get_skill_by_id(skill_id)
    if not existing:
        raise HTTPException(404, "Canonical skill not found")

    # Check name uniqueness against other skills
    name_check, _ = repository.list_paginated(search=name, page=1, limit=5)
    if any(s["id"] != skill_id and s["name"].lower() == name.lower() for s in name_check):
        raise HTTPException(409, "Another skill already uses this name")

    embedding_text = f"{name}. {description}" if description else name
    embedding = request.app.state.vector_searcher.make_embedding(embedding_text)

    updated = repository.update_skill(
        skill_id=skill_id,
        name=name,
        description=description,
        category=category,
        embedding=embedding,
    )

    if not updated:
        raise HTTPException(404, "Canonical skill not found")

    (
        request.app.state.alias_map,
        request.app.state.canonical_map,
        request.app.state.description_map,
        request.app.state.category_map,
        request.app.state.aliases_by_canonical,
    ) = repository.load_catalogue()

    SuperAdminAuditRepository().create_log(
        super_admin_id=admin["admin_id"],
        action="update_skill",
        entity_type="canonical_skill",
        entity_id=skill_id,
        details={"name": name, "category": category},
    )

    return {"message": "Canonical skill updated successfully"}

@router.get("/normalization-history")
def get_all_normalization_history(
    search: str = "",
    status: str = "",
    page: int = 1,
    limit: int = 25,
):
    if page < 1 or limit < 1 or limit > 100:
        raise HTTPException(400, "Invalid pagination values")

    repository = NormalizationHistoryRepository()

    items, total = repository.list_all(
        search=search,
        status=status,
        page=page,
        limit=limit,
    )

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "history": items,
    }
@router.get("/unresolved-skills")
def get_all_unresolved_skills(
    search: str = "",
    page: int = 1,
    limit: int = 25,
):
    if page < 1 or limit < 1 or limit > 100:
        raise HTTPException(400, "Invalid pagination values")

    repository = UnresolvedSkillRepository()

    items, total = repository.list_all(
        search=search,
        page=page,
        limit=limit,
    )

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "unresolved_skills": items,
    }
@router.get("/org-skill-review")
def list_org_skills_for_review(
    search: str = "",
    status: str = "",
    page: int = 1,
    limit: int = 25,
):
    """List submitted organization skills for super-admin review.

    Only returns skills with review_status IN ('pending', 'approved', 'rejected').
    'not_submitted' records are always excluded, enforced at the repository level.
    Passing status='not_submitted' is silently treated as no filter (returns all submitted).
    """
    if page < 1 or limit < 1 or limit > 100:
        raise HTTPException(400, "Invalid pagination values")
    # Reject not_submitted as a filter — this endpoint is the review queue only.
    if status == "not_submitted":
        status = ""
    repo = OrganizationSkillRepository()
    items, total = repo.list_for_review(search=search, status_filter=status, page=page, limit=limit)
    return {"total": total, "page": page, "limit": limit, "items": items}


class ApproveOrgSkillRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None


@router.post("/org-skill-review/{skill_id}/approve")
def approve_org_skill(
    skill_id: int,
    payload: ApproveOrgSkillRequest,
    request: Request,
    admin: dict = Depends(get_current_super_admin),
):
    """Approve an org skill: find or create a matching canonical skill."""
    org_repo = OrganizationSkillRepository()
    canonical_repo = CanonicalSkillRepository()

    # 1. Fetch the org skill with its aliases
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT os.id, os.organization_id,
                       COALESCE(os.normalized_skill, os.name) AS skill_name,
                       os.description, os.category,
                       ARRAY_AGG(osa.alias) FILTER (WHERE osa.alias IS NOT NULL)
                FROM organization_skill os
                LEFT JOIN organization_skill_alias osa
                       ON osa.organization_skill_id = os.id
                WHERE os.id = %s
                GROUP BY os.id, os.organization_id, os.normalized_skill,
                         os.name, os.description, os.category;
            """, (skill_id,))
            row = cur.fetchone()

    if not row:
        raise HTTPException(404, "Organization skill not found")

    # Validate: only 'pending' skills can be approved
    with psycopg.connect(**DB_CONFIG) as _chk_conn:
        with _chk_conn.cursor() as _chk_cur:
            _chk_cur.execute(
                "SELECT review_status FROM organization_skill WHERE id = %s;",
                (skill_id,),
            )
            _status_row = _chk_cur.fetchone()
    if _status_row and _status_row[0] != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Only pending skills can be approved (current status: {_status_row[0]})",
        )

    _, _, skill_name, description, category, org_aliases = row
    org_aliases = org_aliases or []

    final_name = (payload.name or skill_name or "").strip()
    final_description = (payload.description or description or "").strip() or None
    final_category = (payload.category or category or "").strip() or None

    if not final_name:
        raise HTTPException(400, "Skill name cannot be empty")

    # 2. Check for existing canonical skill (case-insensitive name match)
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM canonical_skill WHERE LOWER(name) = LOWER(%s) LIMIT 1;",
                (final_name,),
            )
            existing_row = cur.fetchone()

    created_new = False
    if existing_row:
        canonical_id = existing_row[0]
    else:
        # 3. Create new canonical skill with embedding
        embedding_text = f"{final_name}. {final_description}" if final_description else final_name
        embedding = request.app.state.vector_searcher.make_embedding(embedding_text)
        canonical_id = canonical_repo.create_skill(
            name=final_name,
            description=final_description,
            category=final_category,
            embedding=embedding,
        )
        created_new = True
        # Refresh in-memory catalogue cache
        (
            request.app.state.alias_map,
            request.app.state.canonical_map,
            request.app.state.description_map,
            request.app.state.category_map,
            request.app.state.aliases_by_canonical,
        ) = canonical_repo.load_catalogue()

    # 4. Add org aliases to canonical skill (skip duplicates)
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT LOWER(alias) FROM skill_alias WHERE canonical_id = %s;",
                (canonical_id,),
            )
            existing_alias_lower = {r[0] for r in cur.fetchall()}

    for alias_text in org_aliases:
        alias_text = alias_text.strip()
        if alias_text and alias_text.lower() not in existing_alias_lower:
            canonical_repo.add_alias(canonical_id, alias_text)
            existing_alias_lower.add(alias_text.lower())

    # 5. Mark org skill as approved
    org_repo.set_review_status(skill_id, "approved")

    # 6. Audit log
    SuperAdminAuditRepository().create_log(
        super_admin_id=admin["admin_id"],
        action="approve_org_skill",
        entity_type="organization_skill",
        entity_id=skill_id,
        details={"canonical_id": canonical_id, "name": final_name, "created_new": created_new},
    )

    return {
        "message": "Organization skill approved and promoted to canonical catalogue",
        "canonical_id": canonical_id,
        "canonical_name": final_name,
        "created_new": created_new,
    }


@router.post("/org-skill-review/{skill_id}/reject")
def reject_org_skill(
    skill_id: int,
    admin: dict = Depends(get_current_super_admin),
):
    """Reject an org skill — does not delete the organization skill record."""
    org_repo = OrganizationSkillRepository()

    # Validate: only 'pending' skills can be rejected
    with psycopg.connect(**DB_CONFIG) as _r_conn:
        with _r_conn.cursor() as _r_cur:
            _r_cur.execute(
                "SELECT review_status FROM organization_skill WHERE id = %s;",
                (skill_id,),
            )
            _r_row = _r_cur.fetchone()
    if _r_row is None:
        raise HTTPException(404, "Organization skill not found")
    if _r_row[0] != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Only pending skills can be rejected (current status: {_r_row[0]})",
        )

    updated = org_repo.set_review_status(skill_id, "rejected")
    if not updated:
        raise HTTPException(404, "Organization skill not found")

    SuperAdminAuditRepository().create_log(
        super_admin_id=admin["admin_id"],
        action="reject_org_skill",
        entity_type="organization_skill",
        entity_id=skill_id,
        details={"status": "rejected"},
    )
    return {"message": "Organization skill rejected"}

@router.get("/dashboard")
def get_super_admin_dashboard():
    repository = SuperAdminDashboardRepository()
    stats = repository.get_dashboard_stats()

    return {
        "message": "Dashboard statistics retrieved successfully",
        "stats": stats,
    }
