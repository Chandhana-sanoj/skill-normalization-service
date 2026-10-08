import psycopg
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv

load_dotenv()


MODEL_NAME = "BAAI/bge-base-en-v1.5"

DB_CONFIG = {
    "host": "127.0.0.1",
    "dbname": "skill_normalization",
    "user": "postgres",
    "password": os.getenv("DB_PASSWORD"),
}


class VectorSearcher:
    def __init__(self):
        print(f"Loading model: {MODEL_NAME}")
        self.model = SentenceTransformer(MODEL_NAME)

    def search(self, text: str, top_k: int = 5):
        # Generate embedding for the input
        embedding = self.model.encode(
            text,
            normalize_embeddings=True,
        )

        vector = embedding.tolist()

        # Search PostgreSQL using cosine distance
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        name,
                        1 - (embedding <=> %s::vector) AS similarity
                    FROM canonical_skill
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s;
                    """,
                    (vector, vector, top_k),
                )

                return cur.fetchall()


if __name__ == "__main__":
    searcher = VectorSearcher()

    test_inputs = [
        # Exact / short variation cases
        "JavaScript",
        "Java",
        "JS",
        "ECMAScript",
        "React",
        "ReactNative",
        "C#",
        "C sharp",
        "K8s",
        "AWS",
        "GCP",
        "SQL",
        "Postgres",

        # Semantic meaning-based cases
        "management of waste",
        "managing customer relationships",
        "detecting fraudulent transactions",
        "predicting customer churn",
        "managing cloud infrastructure",
        "protecting applications from cyber attacks",
        "analyzing customer satisfaction",
        "analyzing employee performance",
    ]

    for test_input in test_inputs:
        results = searcher.search(test_input, top_k=3)

        print()
        print(f"Input: {test_input}")
        print("-" * 60)

        for rank, (skill_id, name, similarity) in enumerate(
            results,
            start=1,
        ):
            print(
                f"{rank}. {name} "
                f"(ID: {skill_id}, similarity: {similarity:.4f})"
            )
    