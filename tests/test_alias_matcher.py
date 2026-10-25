import pytest

from app.services.alias_matcher import AliasMatcher


@pytest.fixture
def matcher():
    alias_map = {
        "python": {1},
        "py": {1},
        "reactjs": {2},
        "shared alias": {1, 2},
    }
    canonical_map = {1: "Python", 2: "React"}
    return AliasMatcher(alias_map, canonical_map)



def test_canonical_and_alias_match(matcher):
    assert matcher.match("python") == 1
    assert matcher.match("Py") == 1
    assert matcher.match_name(" PY ") == "Python"


def test_unknown_skill_does_not_match(matcher):
    assert matcher.match("not a real skill") is None


def test_input_normalization(matcher):
    assert matcher.match(" Python ") == matcher.match("python")
    assert matcher.match("PYTHON") == matcher.match("python")
    assert matcher.match(" ReactJS ") == 2


def test_ambiguous_alias_does_not_match(matcher):
    assert matcher.match("shared alias") is None
    assert matcher.is_ambiguous("shared alias")
    assert matcher.is_known("shared alias")
