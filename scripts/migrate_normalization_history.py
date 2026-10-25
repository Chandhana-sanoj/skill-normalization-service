"""Migration script: create the normalization_history table.

Run once against the target database:
    python scripts/migrate_normalization_history.py
"""

import sys
import os

# Ensure the project root is on the path so app.core.config is importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import psycopg
from app.core.config import DB_CONFIG

DDL = """
CREATE TABLE IF NOT EXISTS normalization_history (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
    input_skill TEXT NOT NULL,
    normalized_skill TEXT,
    version TEXT,
    description TEXT,
    category TEXT,
    status TEXT NOT NULL DEFAULT 'matched',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_normalization_history_org
    ON normalization_history(organization_id);

CREATE INDEX IF NOT EXISTS idx_normalization_history_created
    ON normalization_history(organization_id, created_at DESC);
"""


def run_migration():
    print("Connecting to database…")
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            print("Running DDL…")
            cur.execute(DDL)
        conn.commit()
    print("Migration complete: normalization_history table is ready.")


if __name__ == "__main__":
    run_migration()
