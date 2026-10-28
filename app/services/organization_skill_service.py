
"""Organization skill operations using the shared embedding model."""

from app.repositories.organization_skill_repository import (
    OrganizationSkillRepository,
)


class OrganizationSkillService:
    def __init__(self, model):
        self.repository = OrganizationSkillRepository()
        self.model = model

    def create_skill(
        self,
        organization_id: int,
        name: str,
        description: str | None = None,
    ) -> int:
        embedding = self.model.make_embedding(name)
        return self.repository.create(
            organization_id=organization_id,
            raw_skill=name,
            normalized_skill=name,
            category=None,
            description=description,
            embedding=embedding,
        )
