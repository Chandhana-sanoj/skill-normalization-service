
import psycopg

from app.core.config import DB_CONFIG


class SuperAdminRepository:
    def __init__(self):
        self.db_config = DB_CONFIG

    def find_by_username(self, username: str) -> dict | None:
        query = """
            SELECT id, username, password_hash, is_active
            FROM public.super_admin
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
            "username": row[1],
            "password_hash": row[2],
            "is_active": row[3],
        }

    def find_by_id(self, admin_id: int) -> dict | None:
        query = """
            SELECT id, username, is_active
            FROM public.super_admin
            WHERE id = %s;
        """

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (admin_id,))
                row = cur.fetchone()

        if row is None:
            return None

        return {
            "id": row[0],
            "username": row[1],
            "is_active": row[2],
        }

    def update_last_login(self, admin_id: int) -> None:
        query = """
            UPDATE public.super_admin
            SET last_login_at = NOW()
            WHERE id = %s;
        """

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (admin_id,))
