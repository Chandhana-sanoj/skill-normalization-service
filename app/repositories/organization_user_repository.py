
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


    def list_all_users(self) -> list[dict]:
        """List users across all organizations."""
        query = """
            SELECT
                ou.id,
                ou.organization_id,
                o.name AS organization_name,
                ou.username,
                ou.role,
                ou.is_active
            FROM organization_user ou
            JOIN organization o
                ON o.id = ou.organization_id
            ORDER BY ou.id DESC;
        """

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()

        return [
            {
                "id": row[0],
                "organization_id": row[1],
                "organization_name": row[2],
                "username": row[3],
                "role": row[4],
                "is_active": row[5],
            }
            for row in rows
        ]

    def update_user_status(
        self,
        user_id: int,
        is_active: bool,
    ) -> bool:
        """Activate or deactivate an organization user."""
        query = """
            UPDATE organization_user
            SET is_active = %s
            WHERE id = %s;
        """

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (is_active, user_id))
                return cur.rowcount > 0
