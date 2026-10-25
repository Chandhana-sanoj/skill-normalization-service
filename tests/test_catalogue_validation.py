from unittest.mock import MagicMock

import psycopg
import pytest

from app.repositories.canonical_skill_repository import CanonicalSkillRepository


def make_connection(canonical_rows, alias_rows):
    cursor = MagicMock()
    cursor.fetchall.side_effect = [canonical_rows, alias_rows]
    connection = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    connection.__enter__.return_value = connection
    return connection, cursor


def test_repository_loads_all_four_catalogue_maps(monkeypatch):
    canonical_rows = [
        (1, "Python", "Programming language", "Programming"),
        (2, "React", None, None),
    ]
    alias_rows = [
        ("Python", 1),
        ("Py", 1),
        ("ReactJS", 2),
    ]
    connection, cursor = make_connection(canonical_rows, alias_rows)
    monkeypatch.setattr("app.repositories.canonical_skill_repository.psycopg.connect",
                        lambda **kwargs: connection)

    alias_map, canonical_map, description_map, category_map = (
        CanonicalSkillRepository().load_catalogue()
    )

    assert canonical_map == {1: "Python", 2: "React"}
    assert description_map == {1: "Programming language", 2: ""}
    assert category_map == {1: "Programming", 2: ""}
    assert alias_map == {"python": {1}, "py": {1}, "reactjs": {2}}
    assert cursor.execute.call_count == 2


def test_repository_wraps_database_errors(monkeypatch):
    def fail_connect(**kwargs):
        raise psycopg.OperationalError("database unavailable")

    monkeypatch.setattr(
        "app.repositories.canonical_skill_repository.psycopg.connect",
        fail_connect,
    )

    with pytest.raises(RuntimeError, match="PostgreSQL"):
        CanonicalSkillRepository().load_catalogue()


def test_alias_conflicts_are_retained_for_explicit_handling(monkeypatch):
    connection, _ = make_connection(
        [(1, "Python", "", "Programming"), (2, "Python variant", "", "Programming")],
        [("shared", 1), ("shared", 2)],
    )
    monkeypatch.setattr(
        "app.repositories.canonical_skill_repository.psycopg.connect",
        lambda **kwargs: connection,
    )

    alias_map, _, _, _ = CanonicalSkillRepository().load_catalogue()
    assert alias_map["shared"] == {1, 2}
