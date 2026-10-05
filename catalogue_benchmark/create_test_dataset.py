import pandas as pd
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

CATALOGUE_PATH = PROJECT_ROOT / "skill_catalogue.xlsx"
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
    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def create_test_input(skill_name):
    skill = clean_text(skill_name)

    # Use a known common alias when available.
    if skill in COMMON_ALIASES:
        return COMMON_ALIASES[skill], "common_alias"

    # Lowercase longer skill names.
    # This tests normalization/embedding robustness.
    if len(skill) > 3:
        return skill.lower(), "lowercase"

    # Keep very short names unchanged.
    return skill, "canonical"


def main():

    if not CATALOGUE_PATH.exists():
        raise FileNotFoundError(
            f"Could not find catalogue file: {CATALOGUE_PATH}"
        )

    print("Loading actual skill catalogue...")

    df = pd.read_excel(CATALOGUE_PATH)

    print(f"Loaded {len(df)} skills.")
    print(f"Columns: {list(df.columns)}")

    required_columns = [
        "ID",
        "Canonical Name",
        "Short Description"
    ]

    for column in required_columns:
        if column not in df.columns:
            raise ValueError(
                f"Missing required column: {column}"
            )

    # Keep actual catalogue rows only.
    df = df.dropna(subset=["Canonical Name"]).copy()

    df["Canonical Name"] = df["Canonical Name"].apply(clean_text)

    # Generate benchmark inputs.
    generated = df["Canonical Name"].apply(create_test_input)

    df["Test Input"] = generated.apply(lambda x: x[0])
    df["Test Type"] = generated.apply(lambda x: x[1])

    test_df = df[
        [
            "ID",
            "Canonical Name",
            "Short Description",
            "Test Input",
            "Test Type"
        ]
    ]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    test_df.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8"
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