
import pandas as pd

from app.repositories.canonical_skill_repository import CanonicalSkillRepository
from app.services.multi_skill_extractor import MultiSkillExtractor
from app.services.normalizer import SkillNormalizer
from app.services.vector_search import VectorSearcher


# -----------------------------
# Configuration
# -----------------------------

INPUT_FILE = "skillset_bulk_test_500.xlsx"
INPUT_SHEET = "bulk_test_500"
OUTPUT_FILE = "bulk_test_results.xlsx"
ORGANIZATION_ID = 1
COMPARE_BASELINE = True


# -----------------------------
# Initialize pipeline components
# -----------------------------

catalogue_repository = CanonicalSkillRepository()

(
    alias_map,
    canonical_map,
    description_map,
    category_map,
) = catalogue_repository.load_catalogue()

multi_skill_extractor = MultiSkillExtractor(
    alias_map=alias_map,
    canonical_map=canonical_map,
)

vector_searcher = VectorSearcher()

normalizer = SkillNormalizer(
    alias_map=alias_map,
    canonical_map=canonical_map,
    vector_searcher=vector_searcher,
    organization_id=ORGANIZATION_ID,
    description_map=description_map,
    category_map=category_map,
)


def get_value(result, key, default=""):
    """Read a field from a dict-style or object-style normalizer result."""
    value = result.get(key) if isinstance(result, dict) else getattr(result, key, None)
    return default if value is None else value


# -----------------------------
# Load test dataset
# -----------------------------

df = pd.read_excel(INPUT_FILE, sheet_name=INPUT_SHEET)
df = df.dropna(subset=["skill_set"])

results = []


# -----------------------------
# Process each input skill set
# -----------------------------

for _, row in df.iterrows():
    original_id = row["id"]
    original_input = str(row["skill_set"]).strip()

    before_skill = ""
    before_status = ""

    # Baseline: normalize the original input unchanged.
    if COMPARE_BASELINE and original_input:
        try:
            before = normalizer.normalize(original_input)
            before_skill = get_value(before, "skill")
            before_status = get_value(before, "status")
        except Exception as exc:
            before_status = f"error: {exc}"

    # Extract individual skills.
    try:
        extracted_skills = multi_skill_extractor.extract(original_input)
    except Exception as exc:
        results.append({
            "id": original_id,
            "original_input": original_input,
            "n_skills": 0,
            "extracted_skill": "",
            "normalized_skill": "",
            "version": "",
            "description": "",
            "category": "",
            "status": "error",
            "before_skill": before_skill,
            "before_status": before_status,
            "error": f"extractor: {exc}",
        })
        continue

    if not extracted_skills:
        results.append({
            "id": original_id,
            "original_input": original_input,
            "n_skills": 0,
            "extracted_skill": "",
            "normalized_skill": "",
            "version": "",
            "description": "",
            "category": "",
            "status": "empty",
            "before_skill": before_skill,
            "before_status": before_status,
            "error": "No skills extracted",
        })
        continue

    seen = set()
    row_results = []

    for extracted_skill in extracted_skills:
        try:
            normalized = normalizer.normalize(extracted_skill)
        except Exception as exc:
            row_results.append({
                "id": original_id,
                "original_input": original_input,
                "extracted_skill": extracted_skill,
                "normalized_skill": "",
                "version": "",
                "description": "",
                "category": "",
                "status": "error",
                "before_skill": "",
                "before_status": "",
                "error": str(exc),
            })
            continue

        skill = get_value(normalized, "skill")
        version = get_value(normalized, "version")

        # Deduplicate skills that normalize to the same skill and version.
        key = (str(skill or extracted_skill).lower(), str(version))

        if key in seen:
            continue

        seen.add(key)

        row_results.append({
            "id": original_id,
            "original_input": original_input,
            "extracted_skill": extracted_skill,
            "normalized_skill": skill,
            "version": version,
            "description": get_value(normalized, "description"),
            "category": get_value(normalized, "category"),
            "status": get_value(normalized, "status"),
            "before_skill": "",
            "before_status": "",
            "error": "",
        })

    for i, result_row in enumerate(row_results):
        result_row["n_skills"] = len(row_results)

        if i == 0:
            result_row["before_skill"] = before_skill
            result_row["before_status"] = before_status

    results.extend(row_results)


# -----------------------------
# Summary and output
# -----------------------------

columns = [
    "id",
    "original_input",
    "n_skills",
    "extracted_skill",
    "normalized_skill",
    "version",
    "description",
    "category",
    "status",
    "before_skill",
    "before_status",
    "error",
]

output_df = pd.DataFrame(results, columns=columns)

split_inputs = output_df[output_df["n_skills"] > 1]["id"].nunique()

print("\n========== BULK TEST SUMMARY ==========")
print(f"Input rows processed : {len(df)}")
print(f"Result rows          : {len(output_df)}")
print(f"Inputs split into 2+ : {split_inputs}")

print("Status counts:")
for status, count in output_df["status"].value_counts().items():
    print(f"  {status or '(blank)'}: {count}")

output_df.to_excel(OUTPUT_FILE, index=False)
print(f"\nFull results saved to {OUTPUT_FILE}")

print("\n========== COPY THE OUTPUT BELOW ==========")
print(output_df.to_csv(sep="\t", index=False))
