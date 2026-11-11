import psycopg
from app.core.config import DB_CONFIG


class SuperAdminDashboardRepository:

    def __init__(self):
        self.db_config = DB_CONFIG

    def get_dashboard_stats(self):

        query = """
            SELECT
                (SELECT COUNT(*)
                 FROM organization
                 WHERE deleted_at IS NULL) AS total_organizations,

                (SELECT COUNT(*)
                 FROM organization
                 WHERE is_active = TRUE
                 AND deleted_at IS NULL) AS active_organizations,

                (SELECT COUNT(*)
                 FROM organization
                 WHERE is_active = FALSE
                 AND deleted_at IS NULL) AS inactive_organizations,

                (SELECT COUNT(*)
                 FROM organization_user) AS total_users,

                (SELECT COUNT(*)
                 FROM canonical_skill) AS total_skills,

                (SELECT COUNT(*)
                 FROM skill_alias) AS total_aliases,

                (SELECT COUNT(*)
                 FROM normalization_history) AS total_normalizations,

                (SELECT COUNT(*)
                 FROM unresolved_skill) AS total_unresolved;
        """

        with psycopg.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                row = cur.fetchone()

        return {
            "total_organizations": row[0],
            "active_organizations": row[1],
            "inactive_organizations": row[2],
            "total_users": row[3],
            "total_skills": row[4],
            "total_aliases": row[5],
            "total_normalizations": row[6],
            "total_unresolved": row[7],
        }