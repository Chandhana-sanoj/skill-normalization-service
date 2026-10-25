from sentence_transformers import SentenceTransformer

from app.repositories.organization_skill_repository import (
    OrganizationSkillRepository,
)


MODEL_NAME = "BAAI/bge-base-en-v1.5"


class OrganizationSkillService:
    def __init__(self):
        self.repository = OrganizationSkillRepository()
        self.model = SentenceTransformer(MODEL_NAME)

    def create_skill(
        self,
        organization_id: int,
        name: str,
        description: str | None = None,
    ) -> int:

        embedding = self.model.encode(
            name,
            normalize_embeddings=True,
        )

        skill_id = self.repository.create(
            organization_id=organization_id,
            name=name,
            description=description,
            embedding=embedding.tolist(),
        )

        return skill_id
