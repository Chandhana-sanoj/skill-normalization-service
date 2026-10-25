"""Migration script: extend organization_skill with raw_skill, normalized_skill,
and category columns.

The existing `description` column is reused as-is.
The existing `name` column is kept and will be kept in sync with
`normalized_skill` (VectorSearcher queries `name` as the skill label).

Safe to run repeatedly (uses IF NOT EXISTS / WHERE NULL guards).

Run once:
    python scripts/alter_organization_skill.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import psycopg
from app.core.config import DB_CONFIG

# language=sql
DDL = """
-- 1. Add the three new columns (nullable; existing rows survive unmodified).
ALTER TABLE organization_skill
    ADD COLUMN IF NOT EXISTS raw_skill        TEXT,
    ADD COLUMN IF NOT EXISTS normalized_skill TEXT,
    ADD COLUMN IF NOT EXISTS category         TEXT;

-- 2. Back-fill raw_skill and normalized_skill from the existing `name` column
--    for any row that was created before this migration.
UPDATE organization_skill
SET
    raw_skill        = name,
    normalized_skill = name
WHERE raw_skill IS NULL
   OR normalized_skill IS NULL;
"""

VERIFY_QUERY = """
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'organization_skill'
  AND column_name IN ('raw_skill', 'normalized_skill', 'category')
ORDER BY column_name;
"""


def run_migration() -> None:
    print("Connecting to database…")
    with psycopg.connect(**DB_CONFIG) as conn:

        # Show current columns so we know the baseline.
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'organization_skill'
                ORDER BY ordinal_position;
                """
            )
            rows = cur.fetchall()
        print("Current organization_skill columns:")
        for col, dtype in rows:
            print(f"  {col}: {dtype}")

        with conn.cursor() as cur:
            print("\nApplying migration DDL…")
            cur.execute(DDL)

        conn.commit()

        # Verify.
        with conn.cursor() as cur:
            cur.execute(VERIFY_QUERY)
            added = [r[0] for r in cur.fetchall()]
        print(f"\nNew columns confirmed present: {added}")

    print(
        "\nMigration complete.\n"
        "organization_skill now has raw_skill, normalized_skill, and category columns.\n"
        "Existing rows have been back-filled from the `name` column."
    )


if __name__ == "__main__":
    run_migration()
