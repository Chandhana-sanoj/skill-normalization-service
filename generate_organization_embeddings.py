import psycopg
from sentence_transformers import SentenceTransformer
from app.core.config import DB_CONFIG

MODEL_NAME = "BAAI/bge-small-en-v1.5"


def main():
    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME, device="cpu")

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name
                FROM public.organization_skill
                ORDER BY id;
            """)
            rows = cur.fetchall()
            print(f"Organization skills found: {len(rows)}")

            if not rows:
                print("No organization skills found. Stopping.")
                return

            for skill_id, name in rows:
                vector = model.encode(
                    name,
                    normalize_embeddings=True,
                )

                cur.execute("""
                    UPDATE public.organization_skill
                    SET embedding_small = %s::vector
                    WHERE id = %s;
                """, (vector.tolist(), skill_id))

                conn.commit()
                print(f"Processed: {name}")

    print("Organization embedding generation finished.")


if __name__ == "__main__":
    main()
