
"""Check the Supabase connection and required Skillbase tables."""

import os
import sys

import psycopg
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "sslmode": "require",
    "connect_timeout": 10,
}

required_values = ("host", "user", "password")

missing = [
    key for key in required_values
    if not DB_CONFIG[key]
]

if missing:
    print(f"Missing environment variables: {', '.join(missing)}")
    sys.exit(1)

print(f"Host: {DB_CONFIG['host']}")
print(f"Port: {DB_CONFIG['port']}")
print(f"Database: {DB_CONFIG['dbname']}")
print(f"Username: {DB_CONFIG['user']}")
print("Password: configured (value hidden)")

tables = [
    "canonical_skill",
    "organization",
    "organization_skill",
    "organization_user",
    "skill_alias",
    "unresolved_skill",
    "normalization_history",
    "canonical_skill_category_import",
    "skill_category_import",
]

try:
    with psycopg.connect(**DB_CONFIG) as conn:
        print("\nDatabase connection: SUCCESS")

        with conn.cursor() as cur:
            for table in tables:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                          AND table_name = %s
                    );
                    """,
                    (table,),
                )

                exists = cur.fetchone()[0]

                if exists:
                    cur.execute(
                        f'SELECT COUNT(*) FROM public."{table}";'
                    )
                    count = cur.fetchone()[0]
                    print(f"{table}: {count} rows")
                else:
                    print(f"{table}: MISSING")

            cur.execute(
                """
                SELECT extversion
                FROM pg_extension
                WHERE extname = 'vector';
                """
            )
            vector = cur.fetchone()
            print(
                "pgvector: installed, version "
                + vector[0]
                if vector
                else "pgvector: NOT INSTALLED"
            )

except Exception as exc:
    print(f"\nDatabase connection: FAILED ({type(exc).__name__})")
    print(str(exc))
    sys.exit(1)
