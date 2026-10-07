import pytest

from app.services.catalogue_loader import load_catalogue
from app.services.normalizer import SkillNormalizer


CATALOGUE_FILE = "skill_catalogue.xlsx"


@pytest.fixture
def normalizer():
    alias_map, canonical_map = load_catalogue(CATALOGUE_FILE)

    return SkillNormalizer(
        alias_map=alias_map,
        canonical_map=canonical_map,
    )


def test_exact_canonical_match(normalizer):
    result = normalizer.normalize("Python")

    assert result["input"] == "Python"
    assert result["skill"] == "Python"
    assert result["version"] is None
    assert result["status"] == "matched"


def test_exact_match_with_whitespace_and_case(normalizer):
    result = normalizer.normalize("   PYTHON   ")

    assert result["skill"] == "Python"
    assert result["version"] is None
    assert result["status"] == "matched"


def test_alias_match(normalizer):
    result = normalizer.normalize("Py")

    assert result["skill"] == "Python"
    assert result["version"] is None
    assert result["status"] == "matched"


def test_versioned_skill(normalizer):
    result = normalizer.normalize("Python 3.10")

    assert result["skill"] == "Python"
    assert result["version"] == "3.10"
    assert result["status"] == "matched"


def test_versioned_java(normalizer):
    result = normalizer.normalize("Java 17")

    assert result["skill"] == "Java"
    assert result["version"] == "17"
    assert result["status"] == "matched"


def test_unknown_skill_is_unresolved(normalizer):
    result = normalizer.normalize("SomeCompletelyUnknownSkill")

    assert result["skill"] is None
    assert result["status"] == "unresolved"


def test_empty_input_is_rejected(normalizer):
    with pytest.raises(ValueError):
        normalizer.normalize("")