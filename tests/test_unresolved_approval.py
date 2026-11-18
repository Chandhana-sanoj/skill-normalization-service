"""Tests for the unresolved skill approval endpoint.

Normal (no-duplicate) approval still creates an organization_skill record.
Duplicate/conflict approval now creates an organization_input_mapping record
instead — never touching organization_skill.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest
from fastapi import HTTPException

import app.api.routes.unresolved as unresolved
from app.api.routes.unresolved import ApproveSuggestionRequest


class FakeCursor:
    def __init__(self, rows):
        self.rows = iter(rows)
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        return next(self.rows, None)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor

    def cursor(self):
        return self.fake_cursor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture
def setup_endpoint(monkeypatch):
    suggestion = {
        "name": "Generated Python",
        "description": "Generated description",
        "category": "Programming",
        "aliases": ["Generated Python"],
    }

    cursor = FakeCursor([
        ("Raw skill input", suggestion),
        None,  # No existing organization skill
    ])

    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        unresolved.psycopg,
        "connect",
        lambda **kwargs: connection,
    )

    skill_repo = MagicMock()
    skill_repo.create_in_transaction.return_value = 123

    canonical_repo = MagicMock()

    mapping_repo = MagicMock()
    mapping_repo.save_in_transaction.return_value = 1

    monkeypatch.setattr(
        unresolved,
        "OrganizationSkillRepository",
        lambda: skill_repo,
    )
    monkeypatch.setattr(
        unresolved,
        "CanonicalSkillRepository",
        lambda: canonical_repo,
    )
    monkeypatch.setattr(
        unresolved,
        "OrganizationInputMappingRepository",
        lambda: mapping_repo,
    )

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                vector_searcher=SimpleNamespace(
                    make_embedding=lambda name: [0.1, 0.2, 0.3]
                )
            )
        )
    )

    current_user = {
        "organization_id": 10,
        "role": "org_admin",
    }

    return {
        "suggestion": suggestion,
        "cursor": cursor,
        "skill_repo": skill_repo,
        "canonical_repo": canonical_repo,
        "mapping_repo": mapping_repo,
        "request": request,
        "current_user": current_user,
    }


def approve(setup, payload):
    return unresolved.approve_unresolved_skill(
        unresolved_id=55,
        payload=payload,
        request=setup["request"],
        current_user=setup["current_user"],
    )


# ── Normal approval (no duplicates) ──────────────────────────────────────────

def test_normal_approval_without_duplicates(setup_endpoint):
    setup = setup_endpoint

    result = approve(
        setup,
        ApproveSuggestionRequest(),
    )

    assert result["organization_skill_id"] == 123
    assert result["name"] == "Generated Python"
    assert result["selected_canonical_skill_id"] is None

    setup["skill_repo"].create_in_transaction.assert_called_once()
    setup["skill_repo"].add_aliases_in_transaction.assert_called_once()
    setup["canonical_repo"].get_skill_by_id.assert_not_called()
    # Mapping repo must NOT be touched on the normal path.
    setup["mapping_repo"].save_in_transaction.assert_not_called()


def test_duplicate_requires_canonical_selection(setup_endpoint):
    setup = setup_endpoint
    setup["suggestion"]["duplicate_check"] = {
        "has_duplicates": True,
        "status": "duplicate_found",
        "matched_canonical_ids": [101],
        "matches": [],
    }

    with pytest.raises(HTTPException) as exc:
        approve(setup, ApproveSuggestionRequest())

    assert exc.value.status_code == 409
    setup["skill_repo"].create_in_transaction.assert_not_called()
    setup["mapping_repo"].save_in_transaction.assert_not_called()


def test_invalid_canonical_selection_is_rejected(setup_endpoint):
    setup = setup_endpoint
    setup["suggestion"]["duplicate_check"] = {
        "has_duplicates": True,
        "status": "duplicate_found",
        "matched_canonical_ids": [101],
        "matches": [],
    }

    with pytest.raises(HTTPException) as exc:
        approve(
            setup,
            ApproveSuggestionRequest(canonical_skill_id=999),
        )

    assert exc.value.status_code == 422
    setup["canonical_repo"].get_skill_by_id.assert_not_called()
    setup["skill_repo"].create_in_transaction.assert_not_called()
    setup["mapping_repo"].save_in_transaction.assert_not_called()


# ── Duplicate path: creates mapping, NOT organization_skill ──────────────────

def test_duplicate_selection_creates_input_mapping(setup_endpoint):
    """Selecting an existing canonical skill must write to organization_input_mapping,
    never to organization_skill."""
    setup = setup_endpoint
    setup["suggestion"]["duplicate_check"] = {
        "has_duplicates": True,
        "status": "duplicate_found",
        "matched_canonical_ids": [101],
        "matches": [],
    }

    setup["canonical_repo"].get_skill_by_id.return_value = {
        "id": 101,
        "name": "Python",
        "description": "Programming language",
        "category": "Technology",
        "aliases": [
            {"id": 1, "alias": "Py"},
            {"id": 2, "alias": "Python 3"},
        ],
    }

    result = approve(
        setup,
        ApproveSuggestionRequest(canonical_skill_id=101),
    )

    # Response must reflect canonical mapping, not an org skill.
    assert result["canonical_skill_id"] == 101
    assert result["canonical_name"] == "Python"
    assert result["mapping"] == "organization_input_mapping"
    assert result["raw_skill"] == "Raw skill input"

    # Mapping repo must have been called with correct scalar arguments.
    call_kwargs = setup["mapping_repo"].save_in_transaction.call_args.kwargs
    assert call_kwargs["organization_id"] == 10
    assert call_kwargs["raw_input"] == "Raw skill input"
    assert call_kwargs["canonical_skill_id"] == 101
    assert "conn" in call_kwargs  # conn is the live transaction connection

    # organization_skill must NOT be created.
    setup["skill_repo"].create_in_transaction.assert_not_called()
    setup["skill_repo"].add_aliases_in_transaction.assert_not_called()

    # The shared canonical catalogue must not be modified.
    executed_sql = " ".join(
        query.lower() for query, _ in setup["cursor"].executed
    )
    assert "insert into canonical_skill" not in executed_sql
    assert "update canonical_skill" not in executed_sql
    assert "delete from canonical_skill" not in executed_sql
    assert "insert into skill_alias" not in executed_sql
    assert "insert into organization_skill" not in executed_sql


def test_duplicate_selection_does_not_create_org_skill(setup_endpoint):
    """Additional guard: organization_skill.create_in_transaction is never
    called when resolving a duplicate."""
    setup = setup_endpoint
    setup["suggestion"]["duplicate_check"] = {
        "has_duplicates": True,
        "status": "duplicate_found",
        "matched_canonical_ids": [101],
        "matches": [],
    }
    setup["canonical_repo"].get_skill_by_id.return_value = {
        "id": 101,
        "name": "Python",
        "description": None,
        "category": None,
        "aliases": [],
    }

    approve(setup, ApproveSuggestionRequest(canonical_skill_id=101))

    setup["skill_repo"].create_in_transaction.assert_not_called()


def test_conflict_allows_admin_to_select_one_matching_skill(setup_endpoint):
    """Conflict (multiple matches): admin selects one; mapping written, no org skill."""
    setup = setup_endpoint
    setup["suggestion"]["duplicate_check"] = {
        "has_duplicates": True,
        "status": "conflict",
        "matched_canonical_ids": [101, 202],
        "matches": [],
    }

    setup["canonical_repo"].get_skill_by_id.return_value = {
        "id": 202,
        "name": "Selected Skill",
        "description": "Selected description",
        "category": "Technology",
        "aliases": [],
    }

    result = approve(
        setup,
        ApproveSuggestionRequest(canonical_skill_id=202),
    )

    assert result["canonical_name"] == "Selected Skill"
    assert result["canonical_skill_id"] == 202
    assert result["mapping"] == "organization_input_mapping"

    # Must use mapping repo, not org skill repo.
    setup["mapping_repo"].save_in_transaction.assert_called_once()
    setup["skill_repo"].create_in_transaction.assert_not_called()


def test_non_admin_cannot_approve(setup_endpoint):
    setup = setup_endpoint
    setup["current_user"]["role"] = "member"

    with pytest.raises(HTTPException) as exc:
        approve(setup, ApproveSuggestionRequest())

    assert exc.value.status_code == 403
    setup["skill_repo"].create_in_transaction.assert_not_called()
    setup["mapping_repo"].save_in_transaction.assert_not_called()
