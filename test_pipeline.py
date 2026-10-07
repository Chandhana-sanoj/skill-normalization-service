from app.services.catalogue_loader import load_catalogue
from app.services.normalizer import SkillNormalizer


CATALOGUE_FILE = "skill_catalogue.xlsx"

alias_map, canonical_map = load_catalogue(CATALOGUE_FILE)

normalizer = SkillNormalizer(
    alias_map=alias_map,
    canonical_map=canonical_map,
)


test_inputs = [
    "Python",
    "Py",
    "   PYTHON   ",
    "Python 3.10",
    "Java 17",
    "SomeCompletelyUnknownSkill",
]


for skill in test_inputs:
    result = normalizer.normalize(skill)

    print("\nInput:", skill)
    print("Output:", result)