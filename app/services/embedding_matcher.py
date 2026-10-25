
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

    def match(self, text: str) -> dict | None:
        results = self.vector_searcher.search(
            text,
            organization_id=self.organization_id,
            top_k=3,
        )

        if not results:
            return None

        best_id, best_name, best_similarity = results[0]

        if best_similarity < self.threshold:
            return None

        return {
            "id": best_id,
            "name": best_name,
            "similarity": best_similarity,
        }
