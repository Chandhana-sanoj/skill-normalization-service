
import os
from collections import defaultdict

import psycopg
from dotenv import load_dotenv

from app.services.preprocessing import normalize_lookup_key

load_dotenv()

DB_CONFIG = {
    "host": "127.0.0.1",
    "dbname": "skill_normalization",
    "user": "postgres",
    "password": os.getenv("DB_PASSWORD"),
}


class CanonicalSkillRepository:
    """Loads canonical skills, descriptions and aliases from PostgreSQL."""

    def __init__(self):
        self.db_config = DB_CONFIG

    def load_catalogue(
        self,
    ) -> tuple[
        dict[str, set[int]],
        dict[int, str],
        dict[int, str],
    ]:
        alias_map: dict[str, set[int]] = defaultdict(set)
        canonical_map: dict[int, str] = {}
        description_map: dict[int, str] = {}

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                # Load canonical skills and descriptions.
                cur.execute("""
                    SELECT id, name, description
                    FROM canonical_skill
                    ORDER BY id;
                """)

                for canonical_id, name, description in cur.fetchall():
                    canonical_id = int(canonical_id)

                    canonical_map[canonical_id] = name.strip()
                    description_map[canonical_id] = (
                        description.strip()
                        if description
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

        return dict(alias_map), canonical_map, description_map
