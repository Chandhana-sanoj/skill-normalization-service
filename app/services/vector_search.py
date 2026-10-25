"""Vector similarity search over canonical and organization skills (pgvector)."""
import psycopg
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from app.core.config import DB_CONFIG

load_dotenv()


MODEL_NAME = "BAAI/bge-base-en-v1.5"

# Closest skills for one embedding: the organization's own skills plus the
# shared canonical catalogue, ranked by cosine similarity.
SEARCH_QUERY = """
    SELECT
        skill_id,
        skill_name,
        similarity
    FROM (
        SELECT
            id AS skill_id,
            name AS skill_name,
            1 - (embedding <=> %s::vector) AS similarity
        FROM organization_skill
        WHERE organization_id = %s
          AND embedding IS NOT NULL

        UNION ALL

        SELECT
            id AS skill_id,
            name AS skill_name,
            1 - (embedding <=> %s::vector) AS similarity
        FROM canonical_skill
        WHERE embedding IS NOT NULL
    ) AS combined_skills
    ORDER BY similarity DESC
    LIMIT %s;
"""


class VectorSearcher:  # pylint: disable=too-few-public-methods
    """Embeds text with the BGE model and finds the closest skills in PostgreSQL."""

    def __init__(self):
        print(f"Loading model: {MODEL_NAME}")
        self.model = SentenceTransformer(MODEL_NAME)

    def search(
        self,
        text: str,
        organization_id: int,
        top_k: int = 3,
    ):
        """Return the top_k closest rows as (skill_id, skill_name, similarity)."""
        embedding = self.model.encode(
            text,
            normalize_embeddings=True,
        )

        vector = embedding.tolist()

        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    SEARCH_QUERY,
                    (
                        vector,
                        organization_id,
                        vector,
                        top_k,
                    ),
                )

                return cur.fetchall()
