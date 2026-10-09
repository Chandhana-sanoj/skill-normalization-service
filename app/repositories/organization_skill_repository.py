import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


DB_CONFIG = {
    "host": "127.0.0.1",
    "dbname": "skill_normalization",
    "user": "postgres",
    "password": os.getenv("DB_PASSWORD"),
}


class OrganizationSkillRepository:
    def __init__(self):
        self.db_config = DB_CONFIG

    def find_by_name(
        self,
        organization_id: int,
        name: str,
    ) -> dict | None:

        query = """
            SELECT
                id,
                name,
                description
            FROM organization_skill
            WHERE organization_id = %s
              AND LOWER(name) = LOWER(%s)
            LIMIT 1;
        """

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (organization_id, name),
                )

                row = cur.fetchone()

        if row is None:
            return None

        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
        }

    def create(
        self,
        organization_id: int,
        name: str,
        description: str | None,
        embedding: list[float],
    ) -> int:

        query = """
            INSERT INTO organization_skill (
                organization_id,
                name,
                description,
                embedding
            )
            VALUES (%s, %s, %s, %s::vector)
            RETURNING id;
        """

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (
                        organization_id,
                        name,
                        description,
                        embedding,
                    ),
                )

                skill_id = cur.fetchone()[0]

        return skill_id
    