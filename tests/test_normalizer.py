import pytest

from app.services.normalizer import SkillNormalizer


class FakeVectorSearcher:
    def __init__(self, results=None):
        self.results = results or []
        self.queries = []

    def search(self, text, organization_id, top_k=3):
        self.queries.append((text, organization_id, top_k))
        return self.results


class FakeUnresolvedRepository:
    def __init__(self):
        self.saved = []

    def save(self, organization_id: int, input_text: str) -> int:
        self.saved.append((organization_id, input_text))
        return len(self.saved)


@pytest.fixture
def normalizer(monkeypatch):
    alias_map = {"python": {1}, "py": {1}, "java": {2}, "waste management": {3}}
    canonical_map = {1: "Python", 2: "Java", 3: "Waste Management"}
    description_map = {1: "Python language", 2: "Java language", 3: "Waste services"}
    category_map = {1: "Programming", 2: "Programming", 3: "Operations"}
    vector_searcher = FakeVectorSearcher()
    instance = SkillNormalizer(
        alias_map=alias_map,
        canonical_map=canonical_map,
        vector_searcher=vector_searcher,
        organization_id=1,
        description_map=description_map,
        category_map=category_map,
    )
    fake_unresolved = FakeUnresolvedRepository()
    instance.unresolved_repository = fake_unresolved
    return instance


def test_exact_canonical_match(normalizer):
    result = normalizer.normalize("Python")
    assert result == {
        "input": "Python",
        "skill": "Python",
        "version": None,
        "description": "Python language",
        "category": "Programming",
        "status": "matched",
    }


def test_exact_match_with_whitespace_and_case(normalizer):
    result = normalizer.normalize("   PYTHON   ")
    assert result["skill"] == "Python"
    assert result["status"] == "matched"


def test_alias_match(normalizer):
    assert normalizer.normalize("Py")["skill"] == "Python"


def test_version_is_passed_in_by_extractor(normalizer):
    result = normalizer.normalize("Python 3.10", version="3.10")
    assert result["skill"] == "Python"
    assert result["version"] == "3.10"
    assert result["status"] == "matched"


def test_unknown_skill_is_unresolved(normalizer):
    result = normalizer.normalize("SomeCompletelyUnknownSkill")
    assert result["skill"] is None
    assert result["status"] == "unresolved"
    assert normalizer.unresolved_repository.saved == [
        (1, "SomeCompletelyUnknownSkill")
    ]


def test_empty_input_is_rejected(normalizer):
    with pytest.raises(ValueError, match="cannot be empty"):
        normalizer.normalize("")


def test_semantic_match(monkeypatch, normalizer):
    normalizer.embedding_matcher.vector_searcher.results = [(3, "Waste Management", 0.91)]
    result = normalizer.normalize("management of waste")
    assert result["skill"] == "Waste Management"
    assert result["category"] == "Operations"
    assert result["status"] == "matched"


def test_version_suffix_is_removed_only_when_supplied(normalizer):
    result = normalizer.normalize("Java 17", version="17")
    assert result["skill"] == "Java"
    assert result["version"] == "17"

