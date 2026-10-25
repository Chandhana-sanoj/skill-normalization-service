"""Repository for storing and retrieving unresolved skills."""

import psycopg
from app.core.config import DB_CONFIG


class UnresolvedSkillRepository:
    def __init__(self):
        self.db_config = DB_CONFIG

    def save(self, organization_id: int, input_text: str) -> int:
        query = """
            INSERT INTO unresolved_skill (
                organization_id,
                input
            )
            VALUES (%s, %s)
            ON CONFLICT (organization_id, LOWER(input))
            DO UPDATE SET input = EXCLUDED.input
            RETURNING id;
        """

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (organization_id, input_text),
                )
                unresolved_id = cur.fetchone()[0]

        return unresolved_id

    def list_by_organization(
        self,
        organization_id: int,
        search: str = "",
        page: int = 1,
        limit: int = 25,
    ) -> tuple[list[dict], int]:
        """Return a paginated list of unresolved skills for an organization.

        Returns (items, total).
        """
        base_where = "WHERE organization_id = %s"
        params: list = [organization_id]

        search_lower = search.strip().lower() if search else ""
        if search_lower:
            base_where += " AND LOWER(input) LIKE %s"
            params.append(f"%{search_lower}%")

        count_query = f"SELECT COUNT(*) FROM unresolved_skill {base_where};"

        offset = (page - 1) * limit
        list_query = f"""
            SELECT id, input
            FROM unresolved_skill
            {base_where}
            ORDER BY id DESC
            LIMIT %s OFFSET %s;
        """

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(count_query, params)
                total = cur.fetchone()[0]

                cur.execute(list_query, params + [limit, offset])
                rows = cur.fetchall()

        items = [
            {
                "id": row[0],
                "rawSkill": row[1],
                # No suggestion or confidence stored — the pipeline never
                # persists its best-guess for unresolved skills.
                "suggestion": None,
            }
            for row in rows
        ]

        return items, total

    def resolve(self, organization_id: int, unresolved_id: int) -> bool:
        """Delete an unresolved skill record once it has been resolved.

        Returns True if a row was deleted, False if it was not found or does
        not belong to the given organization.
        """
        query = """
            DELETE FROM unresolved_skill
            WHERE id = %s
              AND organization_id = %s;
        """

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (unresolved_id, organization_id))
                deleted = cur.rowcount > 0

        return deleted

    def update(
        self, organization_id: int, unresolved_id: int, new_input: str
    ) -> bool:
        """Update the input text of an unresolved skill record.

        Returns True if a row was updated, False if not found or not owned
        by the given organization.
        """
        query = """
            UPDATE unresolved_skill
            SET input = %s
            WHERE id = %s
              AND organization_id = %s;
        """

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (new_input, unresolved_id, organization_id))
                updated = cur.rowcount > 0

        return updated

    def delete(self, organization_id: int, unresolved_id: int) -> bool:
        """Permanently delete an unresolved skill record.

        Returns True if a row was deleted, False if not found or not owned
        by the given organization.
        """
        query = """
            DELETE FROM unresolved_skill
            WHERE id = %s
              AND organization_id = %s;
        """

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (unresolved_id, organization_id))
                deleted = cur.rowcount > 0

        return deleted

    def find_by_input(
        self,
        organization_id: int,
        input_text: str,
        exclude_id: int | None = None,
    ) -> dict | None:
        """Find an unresolved skill by case-insensitive input text match.

        Optionally excludes the record with the given id (for duplicate
        checks during update).  Returns the row dict or None.
        """
        query = """
            SELECT id, input
            FROM unresolved_skill
            WHERE organization_id = %s
              AND LOWER(input) = LOWER(%s)
        """
        params: list = [organization_id, input_text]

        if exclude_id is not None:
            query += " AND id != %s"
            params.append(exclude_id)

        query += " LIMIT 1;"

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()

        if row is None:
            return None
        return {"id": row[0], "rawSkill": row[1]}
