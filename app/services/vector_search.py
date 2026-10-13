import os

import psycopg
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from app.core.config import DB_CONFIG

load_dotenv()


MODEL_NAME = "BAAI/bge-base-en-v1.5"

class VectorSearcher:
    def __init__(self):
        print(f"Loading model: {MODEL_NAME}")
        self.model = SentenceTransformer(MODEL_NAME)

    def search(
        self,
        text: str,
        organization_id: int,
        top_k: int = 3,
    ):
        embedding = self.model.encode(
            text,
            normalize_embeddings=True,
        )

        vector = embedding.tolist()

        query = """
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

        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (
                        vector,
                        organization_id,
                        vector,
                        top_k,
                    ),
                )

                return cur.fetchall()
    