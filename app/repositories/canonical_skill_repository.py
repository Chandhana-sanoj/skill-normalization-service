"""Repository for loading canonical skills, categories, descriptions and aliases."""

from collections import defaultdict

import psycopg

from app.services.preprocessing import normalize_lookup_key
from app.core.config import DB_CONFIG


class CanonicalSkillRepository:
    """Loads canonical skills, categories, descriptions and aliases from PostgreSQL."""

    def __init__(self):
        self.db_config = DB_CONFIG

    def load_catalogue(
        self,
    ) -> tuple[
        dict[str, set[int]],
        dict[int, str],
        dict[int, str],
        dict[int, str],
        dict[int, list[str]],
    ]:
        """Load alias_map, canonical_map, description_map, category_map, and
        aliases_by_canonical_id from PostgreSQL.

        Returns:
            alias_map:              normalized alias -> set of canonical IDs
            canonical_map:          canonical ID -> canonical name
            description_map:        canonical ID -> description
            category_map:           canonical ID -> category
            aliases_by_canonical:   canonical ID -> list of raw alias display names

        Raises:
            RuntimeError: when the database cannot be reached.
        """
        alias_map: dict[str, set[int]] = defaultdict(set)
        canonical_map: dict[int, str] = {}
        description_map: dict[int, str] = {}
        category_map: dict[int, str] = {}
        aliases_by_canonical: dict[int, list[str]] = defaultdict(list)

        try:
            with psycopg.connect(**self.db_config) as conn:
                with conn.cursor() as cur:
                    # Load canonical skills, descriptions and categories.
                    cur.execute("""
                        SELECT id, name, description, category
                        FROM canonical_skill
                        ORDER BY id;
                    """)

                    for canonical_id, name, description, category in cur.fetchall():
                        canonical_id = int(canonical_id)

                        canonical_map[canonical_id] = name.strip()
                        description_map[canonical_id] = (
                            description.strip()
                            if description
                            else ""
                        )
                        category_map[canonical_id] = (
                            category.strip()
                            if category
                            else ""
                        )

                    # Load aliases and their corresponding canonical IDs.
                    cur.execute("""
                        SELECT alias, canonical_id
                        FROM skill_alias
                        ORDER BY id;
                    """)

                    for alias, canonical_id in cur.fetchall():
                        canonical_id_int = int(canonical_id)
                        alias_key = normalize_lookup_key(alias)

                        if alias_key:
                            alias_map[alias_key].add(canonical_id_int)

                        # Store the raw display form for the UI (deduplicated per skill).
                        alias_display = alias.strip() if alias else None
                        if alias_display and alias_display not in aliases_by_canonical[canonical_id_int]:
                            aliases_by_canonical[canonical_id_int].append(alias_display)

        except psycopg.OperationalError as exc:
            raise RuntimeError(
                f"Cannot load skill catalogue from PostgreSQL: {exc}"
            ) from exc

        return (
            dict(alias_map),
            canonical_map,
            description_map,
            category_map,
            dict(aliases_by_canonical),
        )

    def get_category_by_id(self, canonical_id: int) -> str | None:
        """Fetch a category directly from PostgreSQL by canonical skill ID."""
        query = """
            SELECT category
            FROM canonical_skill
            WHERE id = %s;
        """

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (canonical_id,))
                row = cur.fetchone()

        return row[0] if row else None

    def get_aliases_by_canonical_name(self, canonical_name: str) -> list[str]:
        """Return raw alias display names for the given canonical skill name."""
        query = """
            SELECT sa.alias
            FROM skill_alias sa
            JOIN canonical_skill cs ON sa.canonical_id = cs.id
            WHERE cs.name = %s
            ORDER BY sa.id;
        """
        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (canonical_name,))
                rows = cur.fetchall()
        return [row[0].strip() for row in rows if row[0] and row[0].strip()]


    def list_paginated(
        self,
        search: str = "",
        page: int = 1,
        limit: int = 25,
    ) -> tuple[list[dict], int]:
        """Return paginated canonical skills without aliases or embeddings."""
        base_where = "WHERE 1=1"
        params: list = []

        if search.strip():
            base_where += " AND (LOWER(name) LIKE %s OR LOWER(COALESCE(description,'')) LIKE %s)"
            v = f"%{search.strip().lower()}%"
            params.extend([v, v])

        count_query = f"SELECT COUNT(*) FROM canonical_skill {base_where};"
        list_query = f"""
            SELECT id, name, description, category
            FROM canonical_skill
            {base_where}
            ORDER BY name
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
            {"id": row[0], "name": row[1], "description": row[2], "category": row[3]}
            for row in rows
        ]
        return items, total

    def get_skill_by_id(self, skill_id: int) -> dict | None:
        """Return a single canonical skill with its aliases as [{id, alias}]."""
        query = """
            SELECT
                cs.id, cs.name, cs.description, cs.category,
                COALESCE(
                    JSON_AGG(JSON_BUILD_OBJECT('id', sa.id, 'alias', sa.alias) ORDER BY sa.id)
                    FILTER (WHERE sa.id IS NOT NULL),
                    '[]'::json
                ) AS aliases
            FROM canonical_skill cs
            LEFT JOIN skill_alias sa ON sa.canonical_id = cs.id
            WHERE cs.id = %s
            GROUP BY cs.id, cs.name, cs.description, cs.category;
        """
        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (skill_id,))
                row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0], "name": row[1], "description": row[2],
            "category": row[3], "aliases": row[4] if row[4] else [],
        }

    def list_all_skills(self) -> list[dict]:
        """Return all canonical skills with their aliases as {id, alias} objects."""
        query = """
            SELECT
                cs.id,
                cs.name,
                cs.description,
                cs.category,
                COALESCE(
                    JSON_AGG(
                        JSON_BUILD_OBJECT('id', sa.id, 'alias', sa.alias)
                        ORDER BY sa.id
                    ) FILTER (WHERE sa.id IS NOT NULL),
                    '[]'::json
                ) AS aliases
            FROM canonical_skill cs
            LEFT JOIN skill_alias sa
                ON sa.canonical_id = cs.id
            GROUP BY
                cs.id,
                cs.name,
                cs.description,
                cs.category
            ORDER BY cs.name;
        """

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()

        return [
            {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "category": row[3],
                "aliases": row[4] if row[4] else [],
            }
            for row in rows
        ]
    def create_skill(
        self,
        name: str,
        description: str | None,
        category: str | None,
        embedding: list[float],
    ) -> int:

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "LOCK TABLE canonical_skill IN EXCLUSIVE MODE;"
                )

                cur.execute(
                    "SELECT COALESCE(MAX(id), 0) + 1 FROM canonical_skill;"
                )
                new_id = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO canonical_skill
                        (id, name, description, category, embedding)
                    VALUES (%s, %s, %s, %s, %s::vector);
                    """,
                    (new_id, name, description, category, embedding),
                )

        return new_id

    def add_alias(self, canonical_id: int, alias: str) -> int:
        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO skill_alias (alias, canonical_id)
                    VALUES (%s, %s)
                    RETURNING id;
                    """,
                    (alias, canonical_id),
                )
                alias_id = cur.fetchone()[0]

        return alias_id

    def delete_alias(self, alias_id: int, canonical_id: int) -> bool:
        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM skill_alias
                    WHERE id = %s AND canonical_id = %s
                    RETURNING id;
                    """,
                    (alias_id, canonical_id),
                )
                return cur.fetchone() is not None

    def list_aliases(self, canonical_id: int) -> list[dict]:
        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, alias
                    FROM skill_alias
                    WHERE canonical_id = %s
                    ORDER BY alias;
                    """,
                    (canonical_id,),
                )
                rows = cur.fetchall()

        return [
            {"id": row[0], "alias": row[1]}
            for row in rows
        ]
    def update_skill(
        self,
        skill_id: int,
        name: str,
        description: str | None,
        category: str | None,
        embedding: list[float],
    ) -> bool:
        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE canonical_skill
                    SET name = %s,
                        description = %s,
                        category = %s,
                        embedding = %s::vector
                    WHERE id = %s
                    RETURNING id;
                    """,
                    (name, description, category, embedding, skill_id),
                )
                return cur.fetchone() is not None
