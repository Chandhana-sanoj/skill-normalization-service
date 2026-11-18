
from unittest import result

from app.services.duplicate_checker import check_duplicates


def test_canonical_name_duplicate():
    result = check_duplicates(
        suggestion={
            "name": "Python",
            "aliases": ["Python Programming"],
        },
        canonical_map={1: "Python"},
        alias_map={},
    )

    assert result["has_duplicates"] is True
    assert result["status"] == "duplicate_found"
    assert result["matches"][0]["canonical_skill_id"] == 1
    assert result["matches"][0]["match_type"] == "existing_canonical_name"


def test_existing_alias_duplicate():
    result = check_duplicates(
        suggestion={
            "name": "Py",
            "aliases": ["Python"],
        },
        canonical_map={1: "Python"},
        alias_map={"py": {1}},
    )

    assert result["has_duplicates"] is True
    assert any(
        match["match_type"] == "existing_alias"
        for match in result["matches"]
    )


def test_no_duplicates():
    result = check_duplicates(
        suggestion={
            "name": "New Skill",
            "aliases": ["New Skill", "NS"],
        },
        canonical_map={1: "Python"},
        alias_map={"py": {1}},
    )

    assert result["has_duplicates"] is False
    assert result["status"] == "no_duplicate"
    assert result["matches"] == []


def test_multiple_canonical_skills_are_detected():
    result = check_duplicates(
        suggestion={
            "name": "Py",
            "aliases": ["Python"],
        },
        canonical_map={
            1: "Python",
            2: "Py",
        },
        alias_map={"py": {1}},
    )

    matched_ids = {
        match["canonical_skill_id"]
        for match in result["matches"]
    }

    assert result["has_duplicates"] is True
    assert 1 in matched_ids
    assert 2 in matched_ids


def test_same_value_in_canonical_and_alias_maps():
    result = check_duplicates(
        suggestion={
            "name": "Python",
            "aliases": [],
        },
        canonical_map={1: "Python"},
        alias_map={"python": {1}},
    )

    assert len(result["matches"]) == 1
    assert result["matches"][0]["match_type"] == "existing_canonical_name"