from app.repositories.organization_skill_repository import (
    OrganizationSkillRepository,
)


repository = OrganizationSkillRepository()


result = repository.find_by_name(
    organization_id=1,
    name="Test Internal Platform",
)

print(result)


result = repository.find_by_name(
    organization_id=1,
    name="test internal platform",
)

print(result)


result = repository.find_by_name(
    organization_id=1,
    name="Python",
)

print(result)