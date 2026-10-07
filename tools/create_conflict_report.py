import pandas as pd
from pathlib import Path


CATALOGUE_FILE = Path("skill_catalogue.xlsx")
OUTPUT_FILE = Path("alias_conflicts.xlsx")


canonical_df = pd.read_excel(
    CATALOGUE_FILE,
    sheet_name="canonical_skill"
)

alias_df = pd.read_excel(
    CATALOGUE_FILE,
    sheet_name="skill_alias"
)


canonical_names = dict(
    zip(
        canonical_df["ID"],
        canonical_df["Canonical Name"]
    )
)


rows = []

for _, row in alias_df.iterrows():
    canonical_id = int(row["ID"])
    aliases = str(row["Aliases"])

    for alias in aliases.split("|"):
        alias = alias.strip()

        if not alias:
            continue

        rows.append({
            "Alias": alias.lower(),
            "Canonical ID": canonical_id,
            "Canonical Name": canonical_names[canonical_id],
        })


df = pd.DataFrame(rows)

conflict_counts = (
    df.groupby("Alias")["Canonical ID"]
    .nunique()
)

conflicting_aliases = conflict_counts[
    conflict_counts > 1
].index


conflicts = df[
    df["Alias"].isin(conflicting_aliases)
].sort_values(
    ["Alias", "Canonical ID"]
)


conflicts.to_excel(
    OUTPUT_FILE,
    index=False
)


print(f"Conflicting aliases: {len(conflicting_aliases)}")
print(f"Conflict rows: {len(conflicts)}")
print(f"Saved to: {OUTPUT_FILE}")