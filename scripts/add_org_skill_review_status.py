"""Migration: add review_status column to organization_skill.

Safe to run repeatedly — uses ADD COLUMN IF NOT EXISTS.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import psycopg
from app.core.config import DB_CONFIG

DDL = """
ALTER TABLE organization_skill
    ADD COLUMN IF NOT EXISTS review_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (review_status IN ('pending', 'approved', 'rejected'));
"""

VERIFY = """
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'organization_skill'
  AND column_name = 'review_status';
"""

def run():
    print("Connecting to database…")
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
        conn.commit()
        with conn.cursor() as cur:
            cur.execute(VERIFY)
            row = cur.fetchone()
            if row:
                print(f"Column verified: {row[0]} ({row[1]}, default={row[2]})")
            else:
                print("WARNING: column not found after migration")
    print("Migration complete.")

if __name__ == "__main__":
    run()
