import pandas as pd

from app.services.catalogue_loader import load_catalogue


CATALOGUE_FILE = "skill_catalogue.xlsx"


def test_catalogue_structure():
    canonical_df = pd.read_excel(
        CATALOGUE_FILE,
        sheet_name="canonical_skill"
    )

    alias_df = pd.read_excel(
        CATALOGUE_FILE,
        sheet_name="skill_alias"
    )

    assert len(canonical_df) == 5071
    assert len(alias_df) == 5071

    assert list(canonical_df.columns) == [
        "ID",
        "Canonical Name",
        "Short Description"
    ]

    assert list(alias_df.columns) == [
        "ID",
        "Aliases"
    ]


def test_all_alias_ids_exist_in_canonical_table():
    canonical_df = pd.read_excel(
        CATALOGUE_FILE,
        sheet_name="canonical_skill"
    )

    alias_df = pd.read_excel(
        CATALOGUE_FILE,
        sheet_name="skill_alias"
    )

    canonical_ids = set(canonical_df["ID"])
    alias_ids = set(alias_df["ID"])

    assert alias_ids == canonical_ids


def test_all_canonical_names_are_in_aliases():
    canonical_df = pd.read_excel(
        CATALOGUE_FILE,
        sheet_name="canonical_skill"
    )

    alias_df = pd.read_excel(
        CATALOGUE_FILE,
        sheet_name="skill_alias"
    )

    aliases_by_id = dict(
        zip(
            alias_df["ID"],
            alias_df["Aliases"]
        )
    )

    missing = []

    for _, row in canonical_df.iterrows():
        canonical_id = row["ID"]

        canonical_name = str(
            row["Canonical Name"]
        ).strip().lower()

        aliases = str(
            aliases_by_id[canonical_id]
        ).lower()

        alias_list = [
            alias.strip()
            for alias in aliases.split("|")
        ]

        if canonical_name not in alias_list:
            missing.append(
                (
                    canonical_id,
                    row["Canonical Name"]
                )
            )

    assert missing == []


def test_no_alias_maps_to_multiple_canonical_ids():
    alias_map, _ = load_catalogue(CATALOGUE_FILE)

    conflicts = {
        alias: ids
        for alias, ids in alias_map.items()
        if len(ids) > 1
    }

    assert conflicts == {}