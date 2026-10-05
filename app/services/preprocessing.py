import re


def normalize_input(text: str) -> str:
    """
    Clean the raw skill input without changing its meaning.
    """

    if not isinstance(text, str):
        raise ValueError("Skill input must be a string")

    text = text.strip()
    text = " ".join(text.split())

    return text


def normalize_lookup_key(text: str) -> str:
    """
    Create a normalized key for exact catalogue lookup.
    """

    return normalize_input(text).lower()


def extract_version(text: str) -> tuple[str, str | None]:
    """
    Extract a trailing version from a skill-like input.

    Examples:
        Python 3.10     -> ("Python", "3.10")
        Java 17         -> ("Java", "17")
        React 18        -> ("React", "18")
        Python 3.10.2   -> ("Python", "3.10.2")
        Python          -> ("Python", None)
    """

    text = normalize_input(text)

    version_pattern = r"^(.*?)[\s]+v?(\d+(?:\.\d+){0,2})$"

    match = re.match(version_pattern, text, re.IGNORECASE)

    if not match:
        return text, None

    skill_name = match.group(1).strip()
    version = match.group(2)

    return skill_name, version