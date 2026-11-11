"""Repository for storing and retrieving normalization history."""

import psycopg
from app.core.config import DB_CONFIG


class NormalizationHistoryRepository:
    def __init__(self):
        self.db_config = DB_CONFIG

    def save_batch(self, organization_id: int, results: list[dict]) -> None:
        """Insert a list of normalization result dicts into normalization_history.

        Each result dict is expected to contain the keys produced by
        SkillNormalizer.normalize():  input, skill, version, description,
        category, status.

        Duplicates within the same batch (same organization_id + input_skill +
        normalized_skill) are deduplicated in-memory before the INSERT so no
        unique constraint is required on the table.
        """
        if not results:
            return

        # In-memory dedup: keep first occurrence of (input_skill, normalized_skill).
        seen: set[tuple[str, str | None]] = set()
        unique_rows = []
        for r in results:
            key = (r.get("input", ""), r.get("skill"))
            if key not in seen:
                seen.add(key)
                unique_rows.append(r)

        insert_query = """
            INSERT INTO normalization_history (
                organization_id,
                input_skill,
                normalized_skill,
                version,
                description,
                category,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """

        rows = [
            (
                organization_id,
                r.get("input", ""),
                r.get("skill"),
                r.get("version"),
                r.get("description"),
                r.get("category"),
                r.get("status", "matched"),
            )
            for r in unique_rows
        ]

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.executemany(insert_query, rows)
            conn.commit()

    def list_by_organization(
        self,
        organization_id: int,
        search: str = "",
        status: str = "",
        page: int = 1,
        limit: int = 25,
    ) -> tuple[list[dict], int]:
        """Return a paginated list of normalization history for an organization.

        Returns (items, total).
        Each item dict uses camelCase keys for the frontend:
            id, inputSkill, normalizedSkill, version, description,
            category, status, createdAt.
        """
        base_where = "WHERE organization_id = %s"
        params: list = [organization_id]

        search_lower = search.strip().lower() if search else ""
        if search_lower:
            base_where += (
                " AND (LOWER(input_skill) LIKE %s OR LOWER(normalized_skill) LIKE %s)"
            )
            params.append(f"%{search_lower}%")
            params.append(f"%{search_lower}%")

        if status:
            base_where += " AND status = %s"
            params.append(status)

        count_query = f"SELECT COUNT(*) FROM normalization_history {base_where};"

        offset = (page - 1) * limit
        list_query = f"""
            SELECT
                id,
                input_skill,
                normalized_skill,
                version,
                description,
                category,
                status,
                created_at
            FROM normalization_history
            {base_where}
            ORDER BY created_at DESC
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
                "inputSkill": row[1],
                "normalizedSkill": row[2],
                "version": row[3],
                "description": row[4],
                "category": row[5],
                "status": row[6],
                "createdAt": row[7].isoformat() if row[7] else None,
            }
            for row in rows
        ]

        return items, total

    def list_all(
        self,
        search: str = "",
        status: str = "",
        page: int = 1,
        limit: int = 25,
    ) -> tuple[list[dict], int]:

        base_where = "WHERE 1=1"
        params = []

        if search.strip():
            base_where += """
                AND (
                    LOWER(nh.input_skill) LIKE %s
                    OR LOWER(nh.normalized_skill) LIKE %s
                    OR LOWER(o.name) LIKE %s
                )
            """
            search_value = f"%{search.strip().lower()}%"
            params.extend([search_value, search_value, search_value])

        if status:
            base_where += " AND nh.status = %s"
            params.append(status)

        count_query = f"""
            SELECT COUNT(*)
            FROM normalization_history nh
            LEFT JOIN organization o ON o.id = nh.organization_id
            {base_where};
        """

        list_query = f"""
            SELECT
                nh.id,
                nh.organization_id,
                o.name AS organization_name,
                nh.input_skill,
                nh.normalized_skill,
                nh.version,
                nh.description,
                nh.category,
                nh.status,
                nh.created_at
            FROM normalization_history nh
            LEFT JOIN organization o ON o.id = nh.organization_id
            {base_where}
            ORDER BY nh.created_at DESC
            LIMIT %s OFFSET %s;
        """

        offset = (page - 1) * limit

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(count_query, params)
                total = cur.fetchone()[0]

                cur.execute(list_query, params + [limit, offset])
                rows = cur.fetchall()

        items = [
            {
                "id": row[0],
                "organizationId": row[1],
                "organizationName": row[2],
                "inputSkill": row[3],
                "normalizedSkill": row[4],
                "version": row[5],
                "description": row[6],
                "category": row[7],
                "status": row[8],
                "createdAt": row[9].isoformat() if row[9] else None,
            }
            for row in rows
        ]

        return items, total
