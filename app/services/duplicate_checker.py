
from app.services.preprocessing import normalize_lookup_key


def check_duplicates(
    suggestion: dict,
    canonical_map: dict[int, str],
    alias_map: dict[str, set[int]],
    aliases_by_canonical: dict[int, list[str]] | None = None,
) -> dict:
    """
    Check generated canonical names and aliases against the catalogue.
    """

    aliases_by_canonical = aliases_by_canonical or {}

    canonical_name_map = {}

    for canonical_id, canonical_name in canonical_map.items():
        key = normalize_lookup_key(canonical_name)
        if key:
            canonical_name_map.setdefault(key, set()).add(canonical_id)

    generated_values = []

    name = suggestion.get("name", "")
    if isinstance(name, str) and name.strip():
        generated_values.append((name.strip(), "canonical_name"))

    for alias in suggestion.get("aliases", []):
        if isinstance(alias, str) and alias.strip():
            generated_values.append((alias.strip(), "alias"))

    matches_by_key = {}
    seen_generated_values = set()

    for generated_value, generated_type in generated_values:
        normalized_value = normalize_lookup_key(generated_value)

        if not normalized_value or normalized_value in seen_generated_values:
            continue

        seen_generated_values.add(normalized_value)

        # Check existing canonical names.
        canonical_ids = canonical_name_map.get(normalized_value, set())

        for canonical_id in canonical_ids:
            key = (normalized_value, canonical_id)

            matches_by_key[key] = {
                "generated_value": generated_value,
                "generated_type": generated_type,
                "canonical_skill_id": canonical_id,
                "canonical_name": canonical_map[canonical_id],
                "matched_value": canonical_map[canonical_id],
                "match_type": "existing_canonical_name",
            }

        # Check existing aliases.
        alias_ids = alias_map.get(normalized_value, set())

        for canonical_id in alias_ids:
            key = (normalized_value, canonical_id)

            existing_alias = next(
                (
                    alias
                    for alias in aliases_by_canonical.get(canonical_id, [])
                    if normalize_lookup_key(alias) == normalized_value
                ),
                generated_value,
            )

            matches_by_key.setdefault(
                key,
                {
                    "generated_value": generated_value,
                    "generated_type": generated_type,
                    "canonical_skill_id": canonical_id,
                    "canonical_name": canonical_map.get(canonical_id, ""),
                    "matched_value": existing_alias,
                    "match_type": "existing_alias",
                },
            )

    matches = list(matches_by_key.values())

    matched_canonical_ids = sorted({
        match["canonical_skill_id"]
        for match in matches
    })

    if not matches:
        status = "no_duplicate"
    elif len(matched_canonical_ids) > 1:
        status = "conflict"
    else:
        status = "duplicate_found"

    return {
        "has_duplicates": bool(matches),
        "status": status,
        "matched_canonical_ids": matched_canonical_ids,
        "matches": matches,
    }
