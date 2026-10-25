
import psycopg

from app.core.config import DB_CONFIG


class OrganizationUserRepository:
    def __init__(self):
        self.db_config = DB_CONFIG

    def create(
        self,
        organization_id: int,
        username: str,
        password_hash: str,
        role: str = "org_user",
    ) -> int:
        query = """
            INSERT INTO organization_user (
                organization_id,
                username,
                password_hash,
                role
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (
                        organization_id,
                        username.strip(),
                        password_hash,
                        role,
                    ),
                )
                user_id = cur.fetchone()[0]

        return user_id

    def find_by_username(self, username: str) -> dict | None:
        query = """
            SELECT id, organization_id, username, password_hash, role
            FROM organization_user
            WHERE LOWER(username) = LOWER(%s)
            LIMIT 1;
        """

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (username.strip(),))
                row = cur.fetchone()

        if row is None:
            return None

        return {
            "id": row[0],
            "organization_id": row[1],
            "username": row[2],
            "password_hash": row[3],
            "role": row[4],
        }
