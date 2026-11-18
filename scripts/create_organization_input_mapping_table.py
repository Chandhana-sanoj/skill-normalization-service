"""Migration: create the organization_input_mapping table.

This table stores org-scoped mappings from a raw user input to a canonical
skill selected by an admin during duplicate resolution.  It allows subsequent
normalization of the same input to resolve immediately to the selected
canonical skill without going through the unresolved pipeline again.

Run once per environment:
    python scripts/create_organization_input_mapping_table.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import psycopg
from app.core.config import DB_CONFIG


DDL = """
CREATE TABLE IF NOT EXISTS organization_input_mapping (
    id                 SERIAL       PRIMARY KEY,
    organization_id    INTEGER      NOT NULL
                                    REFERENCES organization(id) ON DELETE CASCADE,
    raw_input          TEXT         NOT NULL,
    canonical_skill_id INTEGER      NOT NULL,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Functional unique index enforces one mapping per (org, lower(raw_input)).
CREATE UNIQUE INDEX IF NOT EXISTS uq_org_input_mapping
    ON organization_input_mapping (organization_id, LOWER(raw_input));

CREATE INDEX IF NOT EXISTS idx_org_input_mapping_org_id
    ON organization_input_mapping (organization_id);
"""


def run() -> None:
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
        conn.commit()
    print("organization_input_mapping table created (or already exists).")


if __name__ == "__main__":
    run()
