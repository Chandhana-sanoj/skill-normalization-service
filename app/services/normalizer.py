"""Skill normalizer: exact match, embedding fallback, and unresolved storage."""

import re

from app.services.preprocessing import normalize_input
from app.services.alias_matcher import AliasMatcher
from app.services.embedding_matcher import EmbeddingMatcher
from app.repositories.unresolved_skill_repository import (
    UnresolvedSkillRepository,
)


class SkillNormalizer:
    """
    Normalize a skill candidate whose version has already been extracted.

    Version extraction belongs to MultiSkillExtractor. This class accepts the
    candidate text and its optional version separately, then performs exact
    matching, embedding fallback, and unresolved-skill storage.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        alias_map,
        canonical_map,
        vector_searcher,
        organization_id: int,
        description_map,
        category_map,
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
        self.category_map = category_map
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

    def get_category(self, canonical_id):
        """Return a category for a canonical skill ID."""
        try:
            canonical_id = int(canonical_id)
        except (TypeError, ValueError):
            return None

        return self.category_map.get(canonical_id) or None

    def get_category_by_name(self, canonical_name):
        """Find a category using the canonical skill name."""
        for canonical_id, name in self.canonical_map.items():
            if name == canonical_name:
                return self.get_category(canonical_id)
        return None

    @staticmethod
    def _build_result(
        cleaned_input: str,
        skill: str | None,
        version: str | None,
        description: str | None,
        category: str | None,
        status: str,
    ) -> dict:
        """Build the result dictionary returned by normalize()."""
        return {
            "input": cleaned_input,
            "skill": skill,
            "version": version,
            "description": description,
            "category": category,
            "status": status,
        }

    @staticmethod
    def _remove_supplied_version(text: str, version: str | None) -> str:
        """
        Remove the version suffix supplied by MultiSkillExtractor.

        This does not discover or parse versions. It only removes the exact
        version value already provided by the extractor.
        """
        if not version:
            return text

        suffix_pattern = re.compile(
            r"\s*\(?\s*" + re.escape(version.strip()) + r"\s*\)?\s*$",
            re.IGNORECASE,
        )
        base_text = suffix_pattern.sub("", text).strip()
        return base_text or text

    def normalize(self, text: str, version: str | None = None) -> dict:
        """
        Normalize one extracted skill candidate.

        Args:
            text: Candidate text produced by MultiSkillExtractor.
            version: Version already extracted by MultiSkillExtractor, if any.

        Returns input, canonical skill, version, description, category, and
        status ("matched" or "unresolved").

        Raises ValueError when the input is not a string or is empty.
        """
        cleaned_input = normalize_input(text)

        if not cleaned_input:
            raise ValueError("Skill input cannot be empty")

        # The extractor owns version parsing. If it supplied a version, remove
        # that known suffix to obtain the skill name; do not parse it again.
        skill_name = self._remove_supplied_version(cleaned_input, version)

        # Exact match first, protecting names such as HTML5, CSS3, and GPT-4o.
        canonical_id = self.matcher.match(skill_name)

        if canonical_id is not None:
            canonical_name = self.matcher.match_name(skill_name)
            return self._build_result(
                cleaned_input,
                canonical_name,
                version,
                self.get_description(canonical_id),
                self.get_category(canonical_id),
                "matched",
            )

        # Semantic fallback uses the base skill name, never the version suffix.
        embedding_result = self.embedding_matcher.match(skill_name)

        if embedding_result is not None:
            canonical_name = embedding_result["name"]
            return self._build_result(
                cleaned_input,
                canonical_name,
                version,
                self.get_description_by_name(canonical_name),
                self.get_category_by_name(canonical_name),
                "matched",
            )

        # No exact or semantic match: store the original candidate as unresolved.
        self.unresolved_repository.save(
            organization_id=self.organization_id,
            input_text=cleaned_input,
        )

        return self._build_result(
            cleaned_input,
            None,
            version,
            None,
            None,
            "unresolved",
        )
