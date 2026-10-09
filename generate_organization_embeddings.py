import os

import psycopg
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer


load_dotenv()


MODEL_NAME = "BAAI/bge-base-en-v1.5"

DB_CONFIG = {
    "host": "127.0.0.1",
    "dbname": "skill_normalization",
    "user": "postgres",
    "password": os.getenv("DB_PASSWORD"),
}


def generate_embeddings():
    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT id, name
                FROM organization_skill
                WHERE embedding IS NULL;
                """
            )

            skills = cur.fetchall()

            if not skills:
                print("No organization skills need embeddings.")
                return

            for skill_id, skill_name in skills:
                embedding = model.encode(
                    skill_name,
                    normalize_embeddings=True,
                )

                cur.execute(
                    """
                    UPDATE organization_skill
                    SET embedding = %s::vector
                    WHERE id = %s;
                    """,
                    (embedding.tolist(), skill_id),
                )

                print(f"Embedded: {skill_name}")

        conn.commit()

    print("Organization embeddings generated successfully.")


if __name__ == "__main__":
    generate_embeddings()