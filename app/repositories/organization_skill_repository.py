"""Repository for organization-specific skills.

Column layout after alter_organization_skill.py migration:
    id               SERIAL PK
    organization_id  INTEGER FK → organization(id)
    name             TEXT        kept in sync with normalized_skill (VectorSearcher uses it)
    description      TEXT        free-text description / notes
    embedding        vector      embedding of normalized_skill (same text as name)
    raw_skill        TEXT        the skill as the org uses it (added by migration)
    normalized_skill TEXT        canonical / standardized name (added by migration)
    category         TEXT        from the canonical catalogue (added by migration)
"""

import psycopg

from app.core.config import DB_CONFIG


# Column positions returned by every SELECT in this file:
#   0  id
#   1  name
#   2  description
#   3  raw_skill
#   4  normalized_skill
#   5  category

_SELECT_COLS = """
    id,
    name,
    description,
    COALESCE(raw_skill,        name)  AS raw_skill,
    COALESCE(normalized_skill, name)  AS normalized_skill,
    COALESCE(category, '')            AS category
"""


class OrganizationSkillRepository:
    def __init__(self):
        self.db_config = DB_CONFIG

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_dict(row: tuple) -> dict:
        skill_id, name, description, raw_skill, normalized_skill, category = row
        return {
            "id":              skill_id,
            "rawSkill":        raw_skill or name or "",
            "normalizedSkill": normalized_skill or name or "",
            "category":        category or "",
            "description":     description or "",
        }

    # ── Read ──────────────────────────────────────────────────────────────────

    def find_by_name(
        self,
        organization_id: int,
        normalized_name: str,
        exclude_id: int | None = None,
    ) -> dict | None:
        """Find an org skill by case-insensitive normalized_skill match.

        Falls back to the legacy ``name`` column for pre-migration rows.
        ``exclude_id`` lets callers skip the record being updated.
        """
        query = f"""
            SELECT {_SELECT_COLS}
            FROM organization_skill
            WHERE organization_id = %s
              AND LOWER(COALESCE(normalized_skill, name)) = LOWER(%s)
        """
        params: list = [organization_id, normalized_name]

        if exclude_id is not None:
            query += " AND id != %s"
            params.append(exclude_id)

        query += " LIMIT 1;"

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()

        return self._row_to_dict(row) if row else None

    def list_by_organization(
        self,
        organization_id: int,
        search: str = "",
        page: int = 1,
        limit: int = 25,
    ) -> tuple[list[dict], int]:
        """Return a paginated, optionally searched list of org skills."""
        base_where = "WHERE organization_id = %s"
        params: list = [organization_id]

        search_lower = search.strip().lower() if search else ""
        if search_lower:
            base_where += (
                " AND ("
                "  LOWER(COALESCE(raw_skill,        name))        LIKE %s"
                "  OR LOWER(COALESCE(normalized_skill, name))     LIKE %s"
                "  OR LOWER(COALESCE(description, ''))            LIKE %s"
                ")"
            )
            like = f"%{search_lower}%"
            params.extend([like, like, like])

        count_query = f"SELECT COUNT(*) FROM organization_skill {base_where};"

        offset = (page - 1) * limit
        list_query = f"""
            SELECT {_SELECT_COLS}
            FROM organization_skill
            {base_where}
            ORDER BY COALESCE(raw_skill, name)
            LIMIT %s OFFSET %s;
        """

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(count_query, params)
                total = cur.fetchone()[0]

                cur.execute(list_query, params + [limit, offset])
                rows = cur.fetchall()

        return [self._row_to_dict(r) for r in rows], total

    # ── Write ─────────────────────────────────────────────────────────────────

    def create(
        self,
        organization_id: int,
        raw_skill: str,
        normalized_skill: str,
        category: str | None,
        description: str | None,
        embedding: list[float],
    ) -> int:
        """Insert a new org skill and return its id."""
        query = """
            INSERT INTO organization_skill (
                organization_id,
                name,
                description,
                embedding,
                raw_skill,
                normalized_skill,
                category
            )
            VALUES (%s, %s, %s, %s::vector, %s, %s, %s)
            RETURNING id;
        """
        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (
                        organization_id,
                        normalized_skill,  # name = normalized_skill (VectorSearcher compat)
                        description,
                        embedding,
                        raw_skill,
                        normalized_skill,
                        category,
                    ),
                )
                skill_id = cur.fetchone()[0]

        return skill_id

    def create_in_transaction(
        self,
        conn: "psycopg.Connection",
        organization_id: int,
        raw_skill: str,
        normalized_skill: str,
        category: str | None,
        description: str | None,
        embedding: list[float],
    ) -> int:
        """Insert a new org skill within an already-open connection.

        Use this to share a transaction with other statements (e.g. the
        promote-unresolved endpoint).
        """
        query = """
            INSERT INTO organization_skill (
                organization_id,
                name,
                description,
                embedding,
                raw_skill,
                normalized_skill,
                category
            )
            VALUES (%s, %s, %s, %s::vector, %s, %s, %s)
            RETURNING id;
        """
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    organization_id,
                    normalized_skill,
                    description,
                    embedding,
                    raw_skill,
                    normalized_skill,
                    category,
                ),
            )
            return cur.fetchone()[0]

    def update(
        self,
        organization_id: int,
        skill_id: int,
        raw_skill: str,
        normalized_skill: str,
        category: str | None,
        description: str | None,
        embedding: list[float],
    ) -> bool:
        """Update an org skill.  Returns True if a row was matched and updated."""
        query = """
            UPDATE organization_skill
            SET name             = %s,
                description      = %s,
                embedding        = %s::vector,
                raw_skill        = %s,
                normalized_skill = %s,
                category         = %s
            WHERE id = %s
              AND organization_id = %s;
        """
        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (
                        normalized_skill,
                        description,
                        embedding,
                        raw_skill,
                        normalized_skill,
                        category,
                        skill_id,
                        organization_id,
                    ),
                )
                return cur.rowcount > 0

    def delete(self, organization_id: int, skill_id: int) -> bool:
        """Permanently delete an org skill.  Returns True if a row was deleted."""
        query = """
            DELETE FROM organization_skill
            WHERE id = %s
              AND organization_id = %s;
        """
        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (skill_id, organization_id))
                return cur.rowcount > 0
