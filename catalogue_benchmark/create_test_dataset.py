
import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Allow imports from the project root when this script is run directly.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.repositories.canonical_skill_repository import (
    CanonicalSkillRepository,
)

OUTPUT_PATH = PROJECT_ROOT / "catalogue_benchmark" / "test_cases.csv"


# Only aliases that are reasonably unambiguous.
COMMON_ALIASES = {
    "JavaScript": "JS",
    "TypeScript": "TS",
    "PostgreSQL": "Postgres",
    "MongoDB": "Mongo DB",
    "Kubernetes": "K8s",
    "React": "ReactJS",
    "C#": "C sharp",
    "C++": "CPP",
}


def clean_text(text):
    """Strip leading/trailing whitespace and normalize internal spaces."""
    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def create_test_input(skill_name):
    """Generate a test input and identify the transformation applied."""
    skill = clean_text(skill_name)

    # Use a known common alias when available.
    if skill in COMMON_ALIASES:
        return COMMON_ALIASES[skill], "common_alias"

    # Lowercase longer skill names to test normalization robustness.
    if len(skill) > 3:
        return skill.lower(), "lowercase"

    # Keep very short names unchanged.
    return skill, "canonical"


def load_catalogue_from_postgres():
    """Load canonical skills and descriptions from PostgreSQL."""
    print("Loading actual skill catalogue from PostgreSQL...")

    _, canonical_map, description_map, _ = (
        CanonicalSkillRepository().load_catalogue()
    )

    rows = [
        {
            "ID": skill_id,
            "Canonical Name": name,
            "Short Description": description_map.get(skill_id, ""),
        }
        for skill_id, name in canonical_map.items()
        if isinstance(name, str) and name.strip()
    ]

    if not rows:
        raise RuntimeError(
            "No canonical skills were loaded from PostgreSQL."
        )

    df = pd.DataFrame(
        rows,
        columns=[
            "ID",
            "Canonical Name",
            "Short Description",
        ],
    )

    df["Canonical Name"] = df["Canonical Name"].apply(clean_text)
    df["Short Description"] = df["Short Description"].fillna("")

    # Guard against duplicate canonical names in the generated dataset.
    df = df.drop_duplicates(subset=["Canonical Name"]).copy()

    print(f"Loaded {len(df)} canonical skills from PostgreSQL.")
    return df


def main():
    df = load_catalogue_from_postgres()

    # Generate benchmark inputs.
    generated = df["Canonical Name"].apply(create_test_input)

    df["Test Input"] = generated.apply(lambda item: item[0])
    df["Test Type"] = generated.apply(lambda item: item[1])

    test_df = df[
        [
            "ID",
            "Canonical Name",
            "Short Description",
            "Test Input",
            "Test Type",
        ]
    ].copy()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    test_df.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8",
    )

    print("\nTest dataset created successfully.")
    print(f"Rows: {len(test_df)}")
    print(f"Saved to: {OUTPUT_PATH}")

    print("\nTest type distribution:")
    print(test_df["Test Type"].value_counts())

    print("\nFirst 30 rows:")
    print(test_df.head(30).to_string(index=False))


if __name__ == "__main__":
    main()
