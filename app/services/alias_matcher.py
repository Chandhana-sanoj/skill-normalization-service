from app.services.preprocessing import normalize_lookup_key


class AliasMatcher:
    """
    Exact canonical/alias matcher.

    Matching is intentionally deterministic:
    - one canonical ID for an alias -> matched
    - multiple canonical IDs for an alias -> ambiguous
    - no canonical ID -> unresolved

    Embedding/fuzzy matching belongs in a later fallback layer.
    """

    def __init__(
        self,
        alias_map: dict[str, set[int]],
        canonical_map: dict[int, str] | None = None,
    ):
        self.alias_map = alias_map
        self.canonical_map = canonical_map or {}

    def match(self, text: str) -> int | None:
        """
        Return the canonical ID only for an unambiguous exact alias match.

        Returns None for:
        - unknown aliases
        - aliases currently shared by multiple canonical skills
        """
        lookup_key = normalize_lookup_key(text)
        canonical_ids = self.alias_map.get(lookup_key, set())

        if len(canonical_ids) != 1:
            return None

        return next(iter(canonical_ids))

    def match_name(self, text: str) -> str | None:
        """
        Return the canonical skill name for an unambiguous exact match.
        """
        canonical_id = self.match(text)

        if canonical_id is None:
            return None

        return self.canonical_map.get(canonical_id)

    def is_ambiguous(self, text: str) -> bool:
        """
        Return True when an alias exists under more than one canonical skill.
        """
        lookup_key = normalize_lookup_key(text)
        return len(self.alias_map.get(lookup_key, set())) > 1

    def is_known(self, text: str) -> bool:
        """
        Return True when the normalized input exists in the alias catalogue,
        including ambiguous aliases.
        """
        lookup_key = normalize_lookup_key(text)
        return lookup_key in self.alias_map
    