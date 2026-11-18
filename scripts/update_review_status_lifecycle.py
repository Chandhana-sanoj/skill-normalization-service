"""
Migration: Update review_status on organization_skill

Changes:
  1. Drop old CHECK constraint (only allowed pending/approved/rejected).
  2. Add new CHECK constraint (allows not_submitted/pending/approved/rejected).
  3. Change default from 'pending' to 'not_submitted'.
  4. Backfill existing rows that have review_status = 'pending' to 'not_submitted'
     because they were created before the review workflow existed and were never
     submitted by an org admin.
"""
import sys
sys.path.insert(0, r"c:\Users\hp\Desktop\skill-embedding-trial\skill-normalization-service\skill-normalization-service")

import psycopg
from app.core.config import DB_CONFIG

STEPS = [
    # 1. Drop the old constraint
    (
        "Drop old CHECK constraint",
        "ALTER TABLE organization_skill DROP CONSTRAINT IF EXISTS organization_skill_review_status_check;"
    ),
    # 2. Add new constraint with not_submitted
    (
        "Add new CHECK constraint",
        """ALTER TABLE organization_skill ADD CONSTRAINT organization_skill_review_status_check
           CHECK (review_status IN ('not_submitted', 'pending', 'approved', 'rejected'));"""
    ),
    # 3. Change column default
    (
        "Change column default to not_submitted",
        "ALTER TABLE organization_skill ALTER COLUMN review_status SET DEFAULT 'not_submitted';"
    ),
    # 4. Backfill: existing rows that are 'pending' (created before workflow) → 'not_submitted'
    (
        "Backfill old pending rows to not_submitted",
        "UPDATE organization_skill SET review_status = 'not_submitted' WHERE review_status = 'pending';"
    ),
]

with psycopg.connect(**DB_CONFIG) as conn:
    with conn.cursor() as cur:
        for label, sql in STEPS:
            print(f"  >> {label}...")
            cur.execute(sql)
            if cur.rowcount >= 0 and "UPDATE" in sql:
                print(f"     Rows updated: {cur.rowcount}")
    conn.commit()
    print("All steps committed.")

    # Verify
    with conn.cursor() as cur:
        cur.execute("SELECT column_default FROM information_schema.columns WHERE table_name='organization_skill' AND column_name='review_status'")
        print("Column default now:", cur.fetchone()[0])
        cur.execute("SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='organization_skill'::regclass AND contype='c'")
        print("Constraint:", cur.fetchone())
        cur.execute("SELECT review_status, COUNT(*) FROM organization_skill GROUP BY review_status")
        print("Status counts after migration:", cur.fetchall())
