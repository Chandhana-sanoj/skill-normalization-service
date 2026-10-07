from app.services.preprocessing import (
    normalize_input,
    extract_version,
)
from app.services.alias_matcher import AliasMatcher


class SkillNormalizer:
    """
    Orchestrates preprocessing, exact alias matching,
    and version extraction.

    """

    def __init__(self, alias_map, canonical_map):
        self.matcher = AliasMatcher(
            alias_map=alias_map,
            canonical_map=canonical_map,
        )

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
                "status": "matched",
            }

        # Step 5: Nothing matched.
        # Embedding fallback will be added later.
        return {
            "input": cleaned_input,
            "skill": None,
            "version": version,
            "status": "unresolved",
        }