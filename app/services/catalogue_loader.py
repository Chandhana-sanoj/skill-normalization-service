from collections import defaultdict

import pandas as pd

from app.services.preprocessing import normalize_lookup_key


def load_catalogue(
    file_path: str,
) -> tuple[dict[str, set[int]], dict[int, str], dict[int, str]]:
    """
    Load canonical skills and aliases.

    Returns:
        alias_map: normalized alias -> set of canonical IDs
        canonical_map: canonical ID -> canonical name
        description_map: canonical ID -> description
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
    description_map: dict[int, str] = {}

    for _, row in canonical_df.iterrows():
        canonical_id = int(row["ID"])
        canonical_name = str(row["Canonical Name"]).strip()

        description = row.get("Short Description", "")
        description = (
            str(description).strip()
            if pd.notna(description)
            else ""
        )

        canonical_map[canonical_id] = canonical_name
        description_map[canonical_id] = description

    alias_map: dict[str, set[int]] = defaultdict(set)

    for _, row in alias_df.iterrows():
        canonical_id = int(row["ID"])
        aliases = str(row["Aliases"])

        for alias in aliases.split("|"):
            alias_key = normalize_lookup_key(alias)

            if alias_key:
                alias_map[alias_key].add(canonical_id)

    return dict(alias_map), canonical_map, description_map


def load_alias_map(file_path: str) -> dict[str, set[int]]:
    """
    Backward-compatible helper used by existing tests/code.
    """
    alias_map, _, _ = load_catalogue(file_path)
    return alias_map

