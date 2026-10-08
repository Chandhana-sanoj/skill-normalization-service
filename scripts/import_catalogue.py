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
    # Load canonical skills from Excel
    df = pd.read_excel(
        EXCEL_FILE,
        sheet_name="canonical_skill",
    )

    # Keep only the required columns
    df = df[["ID", "Canonical Name", "Short Description"]]

    # Basic validation
    if df["ID"].duplicated().any():
        raise ValueError("Duplicate canonical IDs found.")

    if df["Canonical Name"].isna().any():
        raise ValueError("Some canonical skills have no name.")

    print(f"Loaded {len(df)} canonical skills from Excel.")

    # Connect to PostgreSQL
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:

            for _, row in df.iterrows():
                cur.execute(
                    """
                    INSERT INTO canonical_skill
                        (id, name, description)
                    VALUES
                        (%s, %s, %s)
                    """,
                    (
                        int(row["ID"]),
                        str(row["Canonical Name"]).strip(),
                        (
                            str(row["Short Description"]).strip()
                            if pd.notna(row["Short Description"])
                            else None
                        ),
                    ),
                )

        conn.commit()

    print("Canonical skills imported successfully.")


if __name__ == "__main__":
    main()