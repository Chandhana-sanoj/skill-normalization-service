"""Basic input cleaning and lookup-key normalization."""

import re


def normalize_input(text: str) -> str:
    """Clean input whitespace without changing its meaning."""
    if not isinstance(text, str):
        raise ValueError("Skill input must be a string")

    return " ".join(text.strip().split())


def normalize_lookup_key(text: str) -> str:
    """Create a normalized key for exact catalogue lookup."""
    return normalize_input(text).lower()


_VERSION_RE = re.compile(
    r"^(?P<skill>.+?)\s+v?(?P<version>\d+(?:\.\d+)*)$",
    re.IGNORECASE,
)

