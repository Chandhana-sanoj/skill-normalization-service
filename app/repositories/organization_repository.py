
import psycopg

from app.core.config import DB_CONFIG


class OrganizationRepository:
    def __init__(self):
        self.db_config = DB_CONFIG

    def exists(self, organization_id: int) -> bool:
        query = """
            SELECT EXISTS (
                SELECT 1
                FROM organization
                WHERE id = %s
            );
        """

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (organization_id,))
                result = cur.fetchone()

        return bool(result[0])
