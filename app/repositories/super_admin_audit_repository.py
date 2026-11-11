
import psycopg

from app.core.config import DB_CONFIG


class SuperAdminAuditRepository:
    def __init__(self):
        self.db_config = DB_CONFIG

    def create_log(
        self,
        super_admin_id: int,
        action: str,
        entity_type: str,
        entity_id: int | None = None,
        details: dict | None = None,
    ) -> None:
        query = """
            INSERT INTO public.super_admin_audit_log (
                super_admin_id,
                action,
                entity_type,
                entity_id,
                details
            )
            VALUES (%s, %s, %s, %s, %s);
        """

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (
                        super_admin_id,
                        action,
                        entity_type,
                        entity_id,
                        psycopg.types.json.Jsonb(details or {}),
                    ),
                )
