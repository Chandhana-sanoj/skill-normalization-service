"""Repository for organisation-specific input → canonical skill mappings.

When an admin resolves a duplicate-flagged unresolved skill by selecting an
existing canonical skill, we store the mapping here instead of creating an
organisation_skill record.  This lets subsequent normalisation requests for
the same (organisation, raw_input) pair resolve immediately to the chosen
canonical skill without re-entering the unresolved pipeline.

Table schema (created by scripts/create_organization_input_mapping_table.py):

    organization_input_mapping
    ──────────────────────────
    id                 SERIAL PK
    organization_id    INTEGER FK → organization(id) ON DELETE CASCADE
    raw_input          TEXT        the original user input (e.g. "pythonn")
    canonical_skill_id INTEGER     the admin-selected canonical skill id
    created_at         TIMESTAMPTZ
    UNIQUE (organization_id, LOWER(raw_input))
"""

import psycopg
from app.core.config import DB_CONFIG


class OrganizationInputMappingRepository:
    def __init__(self) -> None:
        self.db_config = DB_CONFIG

    # ── Write ─────────────────────────────────────────────────────────────────

    def save(
        self,
        organization_id: int,
        raw_input: str,
        canonical_skill_id: int,
    ) -> int:
        """Upsert an input → canonical mapping.

        Returns the id of the inserted or updated row.
        On conflict (same org + same lower-cased input) updates the canonical
        skill id so a later admin decision always wins.
        """
        query = """
            INSERT INTO organization_input_mapping
                (organization_id, raw_input, canonical_skill_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (organization_id, LOWER(raw_input))
            DO UPDATE SET canonical_skill_id = EXCLUDED.canonical_skill_id,
                          created_at         = NOW()
            RETURNING id;
        """
        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (organization_id, raw_input, canonical_skill_id))
                return cur.fetchone()[0]

    def save_in_transaction(
        self,
        conn: "psycopg.Connection",
        organization_id: int,
        raw_input: str,
        canonical_skill_id: int,
    ) -> int:
        """Upsert within an already-open transaction.

        Use this to atomically combine the mapping insert with the
        normalization_history insert and the unresolved_skill delete.
        """
        query = """
            INSERT INTO organization_input_mapping
                (organization_id, raw_input, canonical_skill_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (organization_id, LOWER(raw_input))
            DO UPDATE SET canonical_skill_id = EXCLUDED.canonical_skill_id,
                          created_at         = NOW()
            RETURNING id;
        """
        with conn.cursor() as cur:
            cur.execute(query, (organization_id, raw_input, canonical_skill_id))
            return cur.fetchone()[0]

    # ── Read ──────────────────────────────────────────────────────────────────

    def find(
        self,
        organization_id: int,
        raw_input: str,
    ) -> int | None:
        """Return canonical_skill_id for a given (org, input) pair, or None."""
        query = """
            SELECT canonical_skill_id
            FROM organization_input_mapping
            WHERE organization_id = %s
              AND LOWER(raw_input) = LOWER(%s)
            LIMIT 1;
        """
        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (organization_id, raw_input))
                row = cur.fetchone()
        return row[0] if row else None

    def load_for_organization(
        self,
        organization_id: int,
    ) -> dict[str, int]:
        """Return all mappings for an org as {lower(raw_input): canonical_skill_id}.

        Called at request time by the normalization route so that the
        SkillNormalizer can resolve known inputs without a DB round-trip per
        skill.
        """
        query = """
            SELECT LOWER(raw_input), canonical_skill_id
            FROM organization_input_mapping
            WHERE organization_id = %s;
        """
        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (organization_id,))
                rows = cur.fetchall()
        return {row[0]: row[1] for row in rows}
