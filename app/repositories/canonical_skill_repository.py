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
    ]:
        """Load alias_map, canonical_map, description_map, and category_map from PostgreSQL.

        Returns:
            alias_map:       normalized alias -> set of canonical IDs
            canonical_map:   canonical ID -> canonical name
            description_map: canonical ID -> description
            category_map:    canonical ID -> category

        Raises:
            RuntimeError: when the database cannot be reached.
        """
        alias_map: dict[str, set[int]] = defaultdict(set)
        canonical_map: dict[int, str] = {}
        description_map: dict[int, str] = {}
        category_map: dict[int, str] = {}

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
                        alias_key = normalize_lookup_key(alias)

                        if alias_key:
                            alias_map[alias_key].add(int(canonical_id))

        except psycopg.OperationalError as exc:
            raise RuntimeError(
                f"Cannot load skill catalogue from PostgreSQL: {exc}"
            ) from exc

        return (
            dict(alias_map),
            canonical_map,
            description_map,
            category_map,
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
