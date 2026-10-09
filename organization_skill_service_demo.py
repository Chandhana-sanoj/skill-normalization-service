from app.services.organization_skill_service import (
    OrganizationSkillService,
)


service = OrganizationSkillService()

skill_id = service.create_skill(
    organization_id=1,
    name="Test HR Platform",
    description="A platform used by the HR team.",
)

print("Created organization skill ID:", skill_id)