class EmbeddingMatcher:
    

    def __init__(
        self,
        vector_searcher,
        threshold: float = 0.85,
    ):
        self.vector_searcher = vector_searcher
        self.threshold = threshold

    def match(self, text: str) -> dict | None:
        results = self.vector_searcher.search(
            text,
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