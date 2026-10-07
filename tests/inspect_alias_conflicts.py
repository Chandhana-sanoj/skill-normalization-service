import pandas as pd


CATALOGUE_FILE = "skill_catalogue.xlsx"


alias_df = pd.read_excel(
    CATALOGUE_FILE,
    sheet_name="skill_alias"
)

canonical_df = pd.read_excel(
    CATALOGUE_FILE,
    sheet_name="canonical_skill"
)

canonical_names = dict(
    zip(
        canonical_df["ID"],
        canonical_df["Canonical Name"]
    )
)

alias_to_ids = {}

for _, row in alias_df.iterrows():
    canonical_id = int(row["ID"])
    aliases = str(row["Aliases"])

    for alias in aliases.split("|"):
        alias_key = alias.strip().lower()

        if not alias_key:
            continue

        alias_to_ids.setdefault(alias_key, set()).add(canonical_id)


conflicts = {
    alias: sorted(ids)
    for alias, ids in alias_to_ids.items()
    if len(ids) > 1
}


print(f"Total conflicting aliases: {len(conflicts)}")
print()

for alias, ids in conflicts.items():
    print(f"ALIAS: {alias}")

    for skill_id in ids:
        print(
            f"  {skill_id}: "
            f"{canonical_names.get(skill_id, 'UNKNOWN')}"
        )

    print()