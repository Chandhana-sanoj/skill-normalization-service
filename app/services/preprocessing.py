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


def extract_version(text: str) -> tuple[str, str | None]:
    """Split 'Skill 3.10' into ('Skill', '3.10'), or return (text, None).

    Only strips a trailing bare version number (optionally prefixed with 'v').
    Version-like tokens that are part of a skill name (e.g. HTML5, .NET 8) are
    handled correctly because the regex requires a space before the version.
    """
    match = _VERSION_RE.match(text.strip())
    if match:
        return match.group("skill").strip(), match.group("version")
    return text.strip(), None
