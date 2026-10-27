
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
                FROM public.canonical_skill
                WHERE embedding_small IS NULL
                ORDER BY id;
            """)

            rows = cur.fetchall()
            print(f"Canonical skills needing embeddings: {len(rows)}")

            if not rows:
                print("All canonical skills already have embeddings.")
                return

            for start in range(0, len(rows), 8):
                batch = rows[start:start + 8]
                ids = [row[0] for row in batch]
                names = [row[1] for row in batch]

                vectors = model.encode(
                    names,
                    batch_size=8,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )

                for skill_id, vector in zip(ids, vectors):
                    cur.execute("""
                        UPDATE public.canonical_skill
                        SET embedding_small = %s::vector
                        WHERE id = %s
                          AND embedding_small IS NULL;
                    """, (vector.tolist(), skill_id))

                    if cur.rowcount != 1:
                        raise RuntimeError(
                            f"Expected to update skill id {skill_id}, "
                            f"but updated {cur.rowcount} rows."
                        )

                conn.commit()
                print(
                    f"Processed {min(start + 8, len(rows))}/{len(rows)}"
                )

    print("Canonical embedding generation finished.")


if __name__ == "__main__":
    main()
