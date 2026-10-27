
"""Repository for organization-specific skills.

Embedding storage uses embedding_small (vector(384)) for BGE Small.
The original embedding column is preserved for rollback.
"""

import psycopg

from app.core.config import DB_CONFIG


_SELECT_COLS = """
    id,
    name,
    description,
    COALESCE(raw_skill, name) AS raw_skill,
    COALESCE(normalized_skill, name) AS normalized_skill,
    COALESCE(category, '') AS category
"""


class OrganizationSkillRepository:
    def __init__(self):
        self.db_config = DB_CONFIG

    @staticmethod
    def _row_to_dict(row: tuple) -> dict:
        skill_id, name, description, raw_skill, normalized_skill, category = row
        return {
            "id": skill_id,
            "rawSkill": raw_skill or name or "",
            "normalizedSkill": normalized_skill or name or "",
            "category": category or "",
            "description": description or "",
        }

    def find_by_name(
        self,
        organization_id: int,
        normalized_name: str,
        exclude_id: int | None = None,
    ) -> dict | None:
        """Find an organization skill by normalized name."""
        query = f"""
            SELECT {_SELECT_COLS}
            FROM public.organization_skill
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
        """Return a paginated, optionally searched list of organization skills."""
        base_where = "WHERE organization_id = %s"
        params: list = [organization_id]

        search_lower = search.strip().lower() if search else ""
        if search_lower:
            base_where += """
                AND (
                    LOWER(COALESCE(raw_skill, name)) LIKE %s
                    OR LOWER(COALESCE(normalized_skill, name)) LIKE %s
                    OR LOWER(COALESCE(description, '')) LIKE %s
                )
            """
            like = f"%{search_lower}%"
            params.extend([like, like, like])

        count_query = f"""
            SELECT COUNT(*)
            FROM public.organization_skill
            {base_where};
        """

        offset = (page - 1) * limit
        list_query = f"""
            SELECT {_SELECT_COLS}
            FROM public.organization_skill
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

        return [self._row_to_dict(row) for row in rows], total

    def create(
        self,
        organization_id: int,
        raw_skill: str,
        normalized_skill: str,
        category: str | None,
        description: str | None,
        embedding: list[float],
    ) -> int:
        """Insert a new organization skill and return its ID."""
        query = """
            INSERT INTO public.organization_skill (
                organization_id,
                name,
                description,
                embedding_small,
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
                        normalized_skill,
                        description,
                        embedding,
                        raw_skill,
                        normalized_skill,
                        category,
                    ),
                )
                return cur.fetchone()[0]

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
        """Insert an organization skill within an existing transaction."""
        query = """
            INSERT INTO public.organization_skill (
                organization_id,
                name,
                description,
                embedding_small,
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
        """Update an organization skill."""
        query = """
            UPDATE public.organization_skill
            SET name = %s,
                description = %s,
                embedding_small = %s::vector,
                raw_skill = %s,
                normalized_skill = %s,
                category = %s
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
        """Delete an organization skill."""
        query = """
            DELETE FROM public.organization_skill
            WHERE id = %s
              AND organization_id = %s;
        """

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (skill_id, organization_id))
                return cur.rowcount > 0
