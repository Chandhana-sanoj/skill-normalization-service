from app.repositories.unresolved_skill_repository import (
    UnresolvedSkillRepository,
)


repository = UnresolvedSkillRepository()

first_id = repository.save(
    organization_id=1,
    input_text="Some Completely Unknown Skill",
)

second_id = repository.save(
    organization_id=1,
    input_text="Some Completely Unknown Skill",
)

print("First ID :", first_id)
print("Second ID:", second_id)