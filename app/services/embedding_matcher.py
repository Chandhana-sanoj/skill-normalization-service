
class EmbeddingMatcher:
    def __init__(
        self,
        vector_searcher,
        organization_id: int,
        threshold: float = 0.75,
    ):
        self.vector_searcher = vector_searcher
        self.organization_id = organization_id
        self.threshold = threshold

    def get_candidates(self, text: str, top_k: int = 3) -> list[dict]:
        """Return the top similar skills with their similarity scores."""
        results = self.vector_searcher.search(
            text,
            organization_id=self.organization_id,
            top_k=top_k,
        )

        return [
            {
                "id": skill_id,
                "name": skill_name,
                "similarity": float(similarity),
            }
            for skill_id, skill_name, similarity in results
        ]

    def match(self, text: str) -> dict | None:
        """Return the best candidate only if it meets the threshold."""
        candidates = self.get_candidates(text)

        if not candidates:
            return None

        best_match = candidates[0]

        if best_match["similarity"] < self.threshold:
            return None

        return best_match
