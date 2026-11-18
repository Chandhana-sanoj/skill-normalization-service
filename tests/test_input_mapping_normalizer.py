"""Tests for organisation-specific input mapping in SkillNormalizer.

Verifies that:
- A skill with a saved org input mapping resolves immediately to the canonical
  skill without touching the alias catalogue or embedding matcher.
- A skill WITHOUT a saved mapping falls through to the normal resolution path.
- Mappings from one organisation do not affect another.
"""

from unittest.mock import MagicMock, patch
import pytest

from app.services.normalizer import SkillNormalizer


def _make_normalizer(org_input_mappings=None):
    """Return a SkillNormalizer with minimal mocked dependencies."""
    # canonical_map: id → name
    canonical_map = {
        42: "Python",
        99: "JavaScript",
    }

    # alias_map: lower(alias) → {canonical_id, ...}
    alias_map = {
        "python": {42},
        "js": {99},
    }

    description_map = {42: "General-purpose programming language", 99: None}
    category_map = {42: "Programming Languages", 99: "Programming Languages"}

    vector_searcher = MagicMock()
    # Simulate no embedding match above threshold.
    vector_searcher.get_top_k_similar.return_value = []

    normalizer = SkillNormalizer(
        alias_map=alias_map,
        canonical_map=canonical_map,
        vector_searcher=vector_searcher,
        organization_id=10,
        description_map=description_map,
        category_map=category_map,
        aliases_by_canonical={},
        org_input_mappings=org_input_mappings or {},
    )
    return normalizer


class TestOrgInputMappingResolution:

    def test_known_mapping_resolves_immediately(self):
        """A raw input that matches an org mapping returns 'matched' status."""
        normalizer = _make_normalizer(org_input_mappings={"pythonn": 42})

        with patch.object(normalizer.matcher, "match", return_value=None) as mock_alias, \
             patch.object(normalizer.embedding_matcher, "get_candidates", return_value=[]) as mock_emb, \
             patch.object(normalizer.unresolved_repository, "save") as mock_unresolved:

            result = normalizer.normalize("pythonn")

        assert result["status"] == "matched"
        assert result["skill"] == "Python"
        assert result["input"] == "pythonn"
        assert result["description"] == "General-purpose programming language"
        assert result["category"] == "Programming Languages"

        # Alias matcher and embedding matcher must NOT be called — the mapping
        # short-circuits before reaching them.
        mock_alias.assert_not_called()
        mock_emb.assert_not_called()
        mock_unresolved.assert_not_called()

    def test_mapping_lookup_is_case_insensitive(self):
        """Mapping lookup uses normalize_lookup_key (lower-cased)."""
        normalizer = _make_normalizer(org_input_mappings={"pythonn": 42})

        with patch.object(normalizer.matcher, "match", return_value=None), \
             patch.object(normalizer.embedding_matcher, "get_candidates", return_value=[]):

            result_lower = normalizer.normalize("pythonn")
            result_upper = normalizer.normalize("PYTHONN")
            result_mixed = normalizer.normalize("PyThOnN")

        for result in (result_lower, result_upper, result_mixed):
            assert result["status"] == "matched"
            assert result["skill"] == "Python"

    def test_unknown_input_falls_through_to_normal_pipeline(self):
        """An input NOT in the mapping falls through to alias / embedding matching."""
        normalizer = _make_normalizer(org_input_mappings={"pythonn": 42})

        # "javascript" has no org mapping.
        with patch.object(normalizer.matcher, "match", return_value=99) as mock_alias, \
             patch.object(normalizer.matcher, "match_name", return_value="JavaScript"):

            result = normalizer.normalize("javascript")

        assert result["status"] == "matched"
        assert result["skill"] == "JavaScript"
        # Alias matcher WAS called because there's no org mapping for "javascript".
        mock_alias.assert_called_once()

    def test_empty_mapping_does_not_affect_normal_matching(self):
        """When org_input_mappings is empty, normal alias matching works."""
        normalizer = _make_normalizer(org_input_mappings={})

        with patch.object(normalizer.matcher, "match", return_value=42) as mock_alias, \
             patch.object(normalizer.matcher, "match_name", return_value="Python"):

            result = normalizer.normalize("python")

        assert result["status"] == "matched"
        assert result["skill"] == "Python"
        mock_alias.assert_called_once()

    def test_mapping_is_org_scoped_no_cross_contamination(self):
        """Two normalizers for different orgs have independent mappings."""
        normalizer_org_10 = _make_normalizer(org_input_mappings={"pythonn": 42})
        normalizer_org_20 = _make_normalizer(org_input_mappings={})  # No mapping for org 20

        with patch.object(normalizer_org_10.matcher, "match", return_value=None), \
             patch.object(normalizer_org_10.embedding_matcher, "get_candidates", return_value=[]):

            result_10 = normalizer_org_10.normalize("pythonn")

        with patch.object(normalizer_org_20.matcher, "match", return_value=None), \
             patch.object(normalizer_org_20.embedding_matcher, "get_candidates", return_value=[]), \
             patch.object(normalizer_org_20.unresolved_repository, "save", return_value=1), \
             patch("app.services.normalizer.GroqSkillSuggester") as mock_groq:

            mock_groq.return_value.suggest.side_effect = Exception("No LLM in test")
            result_20 = normalizer_org_20.normalize("pythonn")

        # Org 10 resolves via mapping.
        assert result_10["status"] == "matched"
        assert result_10["skill"] == "Python"

        # Org 20 goes unresolved (no mapping, no alias/embedding match).
        assert result_20["status"] == "unresolved"
        assert result_20["skill"] is None
