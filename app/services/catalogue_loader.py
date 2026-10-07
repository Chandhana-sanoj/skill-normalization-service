from collections import defaultdict

import pandas as pd

from app.services.preprocessing import normalize_lookup_key


def load_catalogue(file_path: str) -> tuple[dict[str, set[int]], dict[int, str]]:
    """
    Load the canonical skill and alias sheets.

    Returns:
        alias_map:
            normalized alias -> set of canonical IDs

            A set is used deliberately. If the current catalogue contains
            the same alias under multiple canonical skills, we do not silently
            choose one and create a wrong match.

        canonical_map:
            canonical ID -> canonical name
    """
    canonical_df = pd.read_excel(
        file_path,
        sheet_name="canonical_skill",
    )

    alias_df = pd.read_excel(
        file_path,
        sheet_name="skill_alias",
    )

    canonical_map: dict[int, str] = {}

    for _, row in canonical_df.iterrows():
        canonical_id = int(row["ID"])
        canonical_name = str(row["Canonical Name"]).strip()
        canonical_map[canonical_id] = canonical_name

    alias_map: dict[str, set[int]] = defaultdict(set)

    for _, row in alias_df.iterrows():
        canonical_id = int(row["ID"])
        aliases = str(row["Aliases"])

        for alias in aliases.split("|"):
            alias_key = normalize_lookup_key(alias)

            if alias_key:
                alias_map[alias_key].add(canonical_id)

    return dict(alias_map), canonical_map


def load_alias_map(file_path: str) -> dict[str, set[int]]:
    """
    Backward-compatible helper used by existing tests/code.
    """
    alias_map, _ = load_catalogue(file_path)
    return alias_map
