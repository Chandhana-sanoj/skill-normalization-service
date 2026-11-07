"""Unit tests for the OrganizationSkillRepository alias methods.

All tests use unittest.mock to avoid a live database connection, following the
same pattern established in test_catalogue_validation.py.
"""

from unittest.mock import MagicMock, call, patch

import pytest

from app.repositories.organization_skill_repository import OrganizationSkillRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conn(fetchall_rows=None, rowcount=0):
    """Return a mock psycopg connection + cursor pair."""
    cur = MagicMock()
    cur.fetchall.return_value = fetchall_rows or []
    cur.fetchone.return_value = (1,)   # default: skill_id = 1
    cur.rowcount = rowcount

    ctx_cur = MagicMock()
    ctx_cur.__enter__ = MagicMock(return_value=cur)
    ctx_cur.__exit__ = MagicMock(return_value=False)

    conn = MagicMock()
    conn.cursor.return_value = ctx_cur
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    return conn, cur


# ---------------------------------------------------------------------------
# get_aliases_for_skills
# ---------------------------------------------------------------------------

class TestGetAliasesForSkills:
    def test_returns_empty_dict_when_skill_ids_empty(self):
        repo = OrganizationSkillRepository()
        result = repo.get_aliases_for_skills(organization_id=1, skill_ids=[])
        assert result == {}

    def test_groups_aliases_under_correct_skill_id(self, monkeypatch):
        rows = [(10, "Python 3"), (10, "Py"), (20, "ReactJS")]
        conn, cur = _make_conn(fetchall_rows=rows)
        monkeypatch.setattr(
            "app.repositories.organization_skill_repository.psycopg.connect",
            lambda **kw: conn,
        )

        result = OrganizationSkillRepository().get_aliases_for_skills(
            organization_id=1, skill_ids=[10, 20]
        )

        assert set(result[10]) == {"Python 3", "Py"}
        assert result[20] == ["ReactJS"]

    def test_skill_with_no_aliases_returns_empty_list(self, monkeypatch):
        """Skills in skill_ids that have no rows get an empty list, not KeyError."""
        conn, cur = _make_conn(fetchall_rows=[])
        monkeypatch.setattr(
            "app.repositories.organization_skill_repository.psycopg.connect",
            lambda **kw: conn,
        )

        result = OrganizationSkillRepository().get_aliases_for_skills(
            organization_id=1, skill_ids=[99]
        )
        assert result == {99: []}

    def test_query_includes_organization_id_scope(self, monkeypatch):
        """The SQL must join on organization_skill to enforce org scoping."""
        conn, cur = _make_conn(fetchall_rows=[])
        monkeypatch.setattr(
            "app.repositories.organization_skill_repository.psycopg.connect",
            lambda **kw: conn,
        )

        OrganizationSkillRepository().get_aliases_for_skills(
            organization_id=42, skill_ids=[1, 2]
        )

        executed_sql = cur.execute.call_args[0][0]
        # Must join with organization_skill and filter by organization_id
        assert "organization_skill" in executed_sql.lower()
        assert "organization_id" in executed_sql.lower()


# ---------------------------------------------------------------------------
# replace_aliases
# ---------------------------------------------------------------------------

class TestReplaceAliases:
    def test_deletes_then_inserts_aliases(self, monkeypatch):
        conn, cur = _make_conn()
        monkeypatch.setattr(
            "app.repositories.organization_skill_repository.psycopg.connect",
            lambda **kw: conn,
        )

        OrganizationSkillRepository().replace_aliases(
            organization_id=1,
            skill_id=10,
            aliases=["Py", "Python 3"],
        )

        # First execute call must be the DELETE
        first_call_sql = cur.execute.call_args_list[0][0][0].strip().upper()
        assert first_call_sql.startswith("DELETE")

        # Subsequent INSERT calls should cover both aliases
        insert_calls = [
            c for c in cur.execute.call_args_list
            if c[0][0].strip().upper().startswith("INSERT")
        ]
        inserted_aliases = {c[0][1][1] for c in insert_calls}
        assert inserted_aliases == {"Py", "Python 3"}

    def test_empty_aliases_clears_all(self, monkeypatch):
        conn, cur = _make_conn()
        monkeypatch.setattr(
            "app.repositories.organization_skill_repository.psycopg.connect",
            lambda **kw: conn,
        )

        OrganizationSkillRepository().replace_aliases(
            organization_id=1, skill_id=10, aliases=[]
        )

        # Only the DELETE should run; no INSERT
        insert_calls = [
            c for c in cur.execute.call_args_list
            if c[0][0].strip().upper().startswith("INSERT")
        ]
        assert insert_calls == []
        assert cur.execute.call_count == 1   # only the DELETE

    def test_whitespace_only_aliases_are_ignored(self, monkeypatch):
        conn, cur = _make_conn()
        monkeypatch.setattr(
            "app.repositories.organization_skill_repository.psycopg.connect",
            lambda **kw: conn,
        )

        OrganizationSkillRepository().replace_aliases(
            organization_id=1, skill_id=10, aliases=["  ", "", "React"]
        )

        insert_calls = [
            c for c in cur.execute.call_args_list
            if c[0][0].strip().upper().startswith("INSERT")
        ]
        inserted = {c[0][1][1] for c in insert_calls}
        assert inserted == {"React"}

    def test_duplicate_aliases_are_deduplicated(self, monkeypatch):
        conn, cur = _make_conn()
        monkeypatch.setattr(
            "app.repositories.organization_skill_repository.psycopg.connect",
            lambda **kw: conn,
        )

        OrganizationSkillRepository().replace_aliases(
            organization_id=1, skill_id=10, aliases=["React", "React", "react"]
        )

        insert_calls = [
            c for c in cur.execute.call_args_list
            if c[0][0].strip().upper().startswith("INSERT")
        ]
        # "React" and "react" are different strings — both kept;
        # second "React" duplicate is removed by the set.
        assert len(insert_calls) == 2

    def test_delete_query_scoped_by_organization(self, monkeypatch):
        conn, cur = _make_conn()
        monkeypatch.setattr(
            "app.repositories.organization_skill_repository.psycopg.connect",
            lambda **kw: conn,
        )

        OrganizationSkillRepository().replace_aliases(
            organization_id=99, skill_id=10, aliases=[]
        )

        delete_sql = cur.execute.call_args_list[0][0][0]
        delete_params = cur.execute.call_args_list[0][0][1]

        # organization_id must appear in the WHERE subquery params
        assert 99 in delete_params


# ---------------------------------------------------------------------------
# add_aliases_in_transaction
# ---------------------------------------------------------------------------

class TestAddAliasesInTransaction:
    def test_inserts_all_clean_aliases(self):
        conn, cur = _make_conn()

        repo = OrganizationSkillRepository()
        repo.add_aliases_in_transaction(conn, organization_skill_id=5, aliases=["Go", "Golang"])

        insert_calls = [
            c for c in cur.execute.call_args_list
            if c[0][0].strip().upper().startswith("INSERT")
        ]
        inserted = {c[0][1][1] for c in insert_calls}
        assert inserted == {"Go", "Golang"}

    def test_skips_empty_strings(self):
        conn, cur = _make_conn()

        repo = OrganizationSkillRepository()
        repo.add_aliases_in_transaction(conn, organization_skill_id=5, aliases=["", "  ", "Go"])

        insert_calls = [
            c for c in cur.execute.call_args_list
            if c[0][0].strip().upper().startswith("INSERT")
        ]
        inserted = {c[0][1][1] for c in insert_calls}
        assert inserted == {"Go"}

    def test_empty_list_produces_no_inserts(self):
        conn, cur = _make_conn()
        repo = OrganizationSkillRepository()
        repo.add_aliases_in_transaction(conn, organization_skill_id=5, aliases=[])
        assert cur.execute.call_count == 0
