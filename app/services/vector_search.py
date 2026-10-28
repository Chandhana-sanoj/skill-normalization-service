
"""Vector similarity search over canonical and organization skills."""

import psycopg
from fastembed import TextEmbedding

from app.core.config import DB_CONFIG

MODEL_NAME = "BAAI/bge-small-en-v1.5"


class VectorSearcher:
    """Embeds text and finds similar skills in PostgreSQL."""

    def __init__(self):
        print(f"Loading embedding model: {MODEL_NAME}")

        self.model = TextEmbedding(model_name=MODEL_NAME)

        print("Embedding model loaded successfully.")

    def make_embedding(self, text: str) -> list[float]:
        """Generate a normalized embedding vector for text."""
        embedding = next(self.model.embed([text], normalize=True))
        return embedding.tolist()

    def search(
        self,
        text: str,
        organization_id: int,
        top_k: int = 3,
    ):
        """Return the top_k closest rows as (skill_id, skill_name, similarity)."""
        vector = self.make_embedding(text)

        search_query = """
            SELECT
                skill_id,
                skill_name,
                similarity
            FROM (
                SELECT
                    id AS skill_id,
                    name AS skill_name,
                    1 - (embedding_small <=> %s::vector) AS similarity
                FROM organization_skill
                WHERE organization_id = %s
                  AND embedding_small IS NOT NULL

                UNION ALL

                SELECT
                    id AS skill_id,
                    name AS skill_name,
                    1 - (embedding_small <=> %s::vector) AS similarity
                FROM canonical_skill
                WHERE embedding_small IS NOT NULL
            ) AS combined_skills
            ORDER BY similarity DESC
            LIMIT %s;
        """

        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    search_query,
                    (vector, organization_id, vector, top_k),
                )
                return cur.fetchall()
