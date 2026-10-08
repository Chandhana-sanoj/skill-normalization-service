import pandas as pd
import psycopg


EXCEL_FILE = "skill_catalogue.xlsx"

DB_CONFIG = {
    "host": "127.0.0.1",
    "dbname": "skill_normalization",
    "user": "postgres",
    "password": "chandhana",
}


def main():
    # Load aliases from Excel
    df = pd.read_excel(
        EXCEL_FILE,
        sheet_name="skill_alias",
    )

    df = df[["ID", "Aliases"]]

    print(f"Loaded {len(df)} alias rows from Excel.")

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:

            # Verify every canonical ID exists
            for _, row in df.iterrows():
                canonical_id = int(row["ID"])

                cur.execute(
                    """
                    SELECT 1
                    FROM canonical_skill
                    WHERE id = %s
                    """,
                    (canonical_id,),
                )

                if cur.fetchone() is None:
                    raise ValueError(
                        f"Canonical skill ID {canonical_id} "
                        f"does not exist in canonical_skill."
                    )

            # Insert individual aliases
            inserted = 0

            for _, row in df.iterrows():
                canonical_id = int(row["ID"])
                aliases = str(row["Aliases"])

                for alias in aliases.split("|"):
                    alias = alias.strip()

                    if not alias:
                        continue

                    cur.execute(
                        """
                        INSERT INTO skill_alias
                            (alias, canonical_id)
                        VALUES
                            (%s, %s)
                        """,
                        (alias, canonical_id),
                    )

                    inserted += 1

        conn.commit()

    print(f"Inserted {inserted} aliases successfully.")


if __name__ == "__main__":
    main()