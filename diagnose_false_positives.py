
import psycopg

from app.core.config import DB_CONFIG
from app.services.vector_search import VectorSearcher


THRESHOLD = 0.75
TOP_K = 3

TEST_CASES = [
    "Code-deploy",
    "Code-build",
    "Auto-scaling",
    "Cloudwatch",
    "Create drawings",
]


def main():
    print("Loading BGE Base model...")
    searcher = VectorSearcher()

    query = """
        SELECT
            id,
            name,
            1 - (embedding <=> %s::vector) AS similarity
        FROM canonical_skill
        WHERE embedding IS NOT NULL
        ORDER BY similarity DESC
        LIMIT %s;
    """

    for input_skill in TEST_CASES:

        embedding = searcher.model.encode(
            input_skill,
            normalize_embeddings=True,
        )

        vector = embedding.tolist()

        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (vector, TOP_K))
                results = cur.fetchall()

        print("\n" + "=" * 75)
        print(f"Input: {input_skill}")
        print("\nTop 3 Matches:")
        print("-" * 75)

        if not results:
            print("No matches found.")
            continue

        for rank, (skill_id, skill_name, similarity) in enumerate(
            results, start=1
        ):
            threshold_status = (
                "PASS" if similarity >= THRESHOLD else "FAIL"
            )

            print(
                f"{rank}. {skill_name:<35}"
                f"| Similarity: {similarity:.4f} "
                f"| Threshold: {threshold_status}"
            )

    print("\nDiagnostic completed. No database records modified.")


if __name__ == "__main__":
    main()
