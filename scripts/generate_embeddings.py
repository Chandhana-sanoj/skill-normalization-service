import psycopg
from sentence_transformers import SentenceTransformer


MODEL_NAME = "BAAI/bge-base-en-v1.5"

DB_CONFIG = {
    "host": "127.0.0.1",
    "dbname": "skill_normalization",
    "user": "postgres",
    "password": "chandhana",
}


def main():
    print(f"Loading model: {MODEL_NAME}")

    model = SentenceTransformer(MODEL_NAME)

    print("Connecting to PostgreSQL...")

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:

            # Get canonical skills that do not have embeddings yet
            cur.execute(
                """
                SELECT id, name
                FROM canonical_skill
                WHERE embedding IS NULL
                ORDER BY id;
                """
            )

            rows = cur.fetchall()

            print(f"Skills needing embeddings: {len(rows)}")

            if not rows:
                print("All canonical skills already have embeddings.")
                return

            ids = [row[0] for row in rows]
            names = [row[1] for row in rows]

            print("Generating embeddings...")

            embeddings = model.encode(
                names,
                batch_size=32,
                show_progress_bar=True,
                normalize_embeddings=True,
            )

            print("Saving embeddings to PostgreSQL...")

            for skill_id, embedding in zip(ids, embeddings):
                vector = embedding.tolist()

                cur.execute(
                    """
                    UPDATE canonical_skill
                    SET embedding = %s
                    WHERE id = %s;
                    """,
                    (vector, skill_id),
                )

        conn.commit()

    print(f"Successfully stored {len(rows)} embeddings.")


if __name__ == "__main__":
    main()