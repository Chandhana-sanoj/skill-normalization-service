"""Regression tests for version-list extraction in the current architecture.

The extractor owns version parsing and returns Candidate.version.
The normalizer receives that value explicitly; preprocessing no longer extracts versions.
"""
import pytest

from app.services import normalizer as normalizer_module
from app.services.multi_skill_extractor import MultiSkillExtractor
from app.services.normalizer import SkillNormalizer


ALIAS_MAP = {
    "react": {1},
    "angular": {2},
    "python": {3},
    "node.js": {4},
    "java": {5},
    "sql": {6},
    "asp.net core": {7},
    "html5": {8},
    "css3": {9},
    "gpt-4o": {10},
}
CANONICAL_MAP = {
    1: "React",
    2: "Angular",
    3: "Python",
    4: "Node.js",
    5: "Java",
    6: "SQL",
    7: "ASP.NET Core",
    8: "HTML5",
    9: "CSS3",
    10: "GPT-4o",
}


class FakeSearcher:
    """Return no semantic matches; tests focus on extraction and exact matching."""

    def search(self, text, organization_id, top_k=3):
        return []


class FakeUnresolvedRepository:
    """Avoid database access when a candidate is unresolved."""

    def save(self, organization_id, input_text):
        return 1


@pytest.fixture
def extractor():
    return MultiSkillExtractor(ALIAS_MAP, CANONICAL_MAP)


@pytest.fixture
def pipeline(monkeypatch, extractor):
    monkeypatch.setattr(
        normalizer_module,
        "UnresolvedSkillRepository",
        FakeUnresolvedRepository,
    )
    normalizer = SkillNormalizer(
        alias_map=ALIAS_MAP,
        canonical_map=CANONICAL_MAP,
        vector_searcher=FakeSearcher(),
        organization_id=1,
        description_map={},
        category_map={},
    )

    def run(text):
        candidates = extractor.extract_detailed(text)
        return [
            normalizer.normalize(candidate.text, version=candidate.version)
            for candidate in candidates
        ]

    return run


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("React (16, 17, 18)", [("React", "16, 17, 18")]),
        ("Python (3.8, 3.10, 3.12)", [("Python", "3.8, 3.10, 3.12")]),
        ("Node.js (16, 18, 20)", [("Node.js", "16, 18, 20")]),
        ("Java (8, 11, 17, 21)", [("Java", "8, 11, 17, 21")]),
        ("React 18, Angular 14", [("React", "18"), ("Angular", "14")]),
        ("Java (11+) and SQL", [("Java", "11+"), ("SQL", None)]),
        ("Angular (2+, 9, 11, 14)", [("Angular", "2+, 9, 11, 14")]),
        ("ASP.NET Core (6.0/7.0/8.0)", [("ASP.NET Core", "6.0, 7.0, 8.0")]),
        ("ASP.NET Core 3.0 & 6.0", [("ASP.NET Core", "3.0, 6.0")]),
        ("React (16 and 17)", [("React", "16, 17")]),
        ("Python (3.12)", [("Python", "3.12")]),
        ("React, Java (11+), Python (3.8, 3.12)",
         [("React", None), ("Java", "11+"), ("Python", "3.8, 3.12")]),
        ("Java (8, SQL)", [("Java", None), ("SQL", None)]),
        ("HTML5", [("HTML5", None)]),
        ("CSS3", [("CSS3", None)]),
        ("GPT-4o", [("GPT-4o", None)]),
        ("React 16, 17, 18 and SQL",
         [("React", "16, 17, 18"), ("SQL", None)]),
    ],
)
def test_extractor_and_normalizer_preserve_versions(pipeline, text, expected):
    results = pipeline(text)
    assert [(result["skill"], result["version"]) for result in results] == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("React (16, 17, 18)", [("16, 17, 18", "React 16, 17, 18")]),
        ("Java (11+) and SQL", [("11+", "Java 11+"), (None, "SQL")]),
        ("React v18", [("18", "React 18")]),
        ("Python 3.10", [("3.10", "Python 3.10")]),
    ],
)
def test_extractor_supplies_version_separately(extractor, text, expected):
    candidates = extractor.extract_detailed(text)
    assert [(candidate.version, candidate.text) for candidate in candidates] == expected


def test_duplicate_aliases_are_deduplicated(extractor):
    assert [
        candidate.text for candidate in extractor.extract_detailed("React, React, React")
    ] == ["React"]


def test_version_is_not_extracted_from_skill_names(extractor):
    for text in ("HTML5", "CSS3", "GPT-4o"):
        candidates = extractor.extract_detailed(text)
        assert len(candidates) == 1
        assert candidates[0].version is None
        assert candidates[0].text == text
