from app.services.preprocessing import (
    normalize_input,
    extract_version,
)
from app.services.alias_matcher import AliasMatcher
from app.services.embedding_matcher import EmbeddingMatcher
from app.repositories.unresolved_skill_repository import (
    UnresolvedSkillRepository,
)


class SkillNormalizer:
    """
    Orchestrates preprocessing, exact alias matching,
    version extraction, embedding fallback,
    and unresolved skill storage.
    """

    def __init__(
        self,
        alias_map,
        canonical_map,
        vector_searcher,
        organization_id: int,
        description_map,
    ):
        self.matcher = AliasMatcher(
            alias_map=alias_map,
            canonical_map=canonical_map,
        )

        self.embedding_matcher = EmbeddingMatcher(
            vector_searcher=vector_searcher,
            organization_id=organization_id,
        )

        self.organization_id = organization_id
        self.canonical_map = canonical_map
        self.description_map = description_map
        self.unresolved_repository = UnresolvedSkillRepository()

    def get_description(self, canonical_id):
        """Return the description for a canonical skill ID."""
        description = self.description_map.get(canonical_id)
        return description or None

    def get_description_by_name(self, canonical_name):
        """Find a description using the canonical skill name."""
        for canonical_id, name in self.canonical_map.items():
            if name == canonical_name:
                return self.get_description(canonical_id)

        return None

    def normalize(self, text: str) -> dict:
        # Step 1: Basic input preprocessing
        cleaned_input = normalize_input(text)

        # Reject empty input
        if not cleaned_input:
            raise ValueError("Skill input cannot be empty")

        # Step 2: Try exact match on the FULL input first.
        # This protects names such as HTML5, CSS3, GPT-4o, etc.
        canonical_id = self.matcher.match(cleaned_input)

        if canonical_id is not None:
            canonical_name = self.matcher.match_name(cleaned_input)

            return {
                "input": cleaned_input,
                "skill": canonical_name,
                "version": None,
                "description": self.get_description(canonical_id),
                "status": "matched",
            }

        # Step 3: Extract a possible version
        skill_name, version = extract_version(cleaned_input)

        # Step 4: Try exact match on the base skill
        canonical_id = self.matcher.match(skill_name)

        if canonical_id is not None:
            canonical_name = self.matcher.match_name(skill_name)

            return {
                "input": cleaned_input,
                "skill": canonical_name,
                "version": version,
                "description": self.get_description(canonical_id),
                "status": "matched",
            }

        # Step 5: Embedding fallback
        embedding_result = self.embedding_matcher.match(skill_name)

        if embedding_result is not None:
            canonical_name = embedding_result["name"]

            return {
                "input": cleaned_input,
                "skill": canonical_name,
                "version": version,
                "description": self.get_description_by_name(
                    canonical_name
                ),
                "status": "matched",
            }

        # Step 6: No exact or semantic match
        # Store the unresolved input for this organization.
        self.unresolved_repository.save(
            organization_id=self.organization_id,
            input_text=cleaned_input,
        )

        return {
            "input": cleaned_input,
            "skill": None,
            "version": version,
            "description": None,
            "status": "unresolved",
        }
    
    