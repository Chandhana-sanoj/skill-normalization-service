
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

    def create_with_admin(
        self,
        organization_name: str,
        username: str,
        password_hash: str,
    ) -> dict:
        organization_query = """
            INSERT INTO organization (name)
            VALUES (%s)
            RETURNING id;
        """

        user_query = """
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
                    organization_query,
                    (organization_name.strip(),),
                )
                organization_id = cur.fetchone()[0]

                cur.execute(
                    user_query,
                    (
                        organization_id,
                        username.strip(),
                        password_hash,
                        "org_admin",
                    ),
                )
                user_id = cur.fetchone()[0]

        return {
            "organization_id": organization_id,
            "user_id": user_id,
            "organization_name": organization_name.strip(),
            "username": username.strip(),
        }
