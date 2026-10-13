import os

import psycopg
from dotenv import load_dotenv
from app.core.config import DB_CONFIG
load_dotenv()



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