from app.services.catalogue_loader import load_catalogue
from app.services.normalizer import SkillNormalizer
from app.services.vector_search import VectorSearcher


CATALOGUE_FILE = "skill_catalogue.xlsx"


alias_map, canonical_map = load_catalogue(CATALOGUE_FILE)

vector_searcher = VectorSearcher()

normalizer = SkillNormalizer(
    alias_map=alias_map,
    canonical_map=canonical_map,
    vector_searcher=vector_searcher,
    organization_id=1,
)


test_cases = [
    "Python",
    "Py",
    "Python 3.10",
    "management of waste",
    "managing cloud infrastructure",
    "SomeCompletelyUnknownSkill",
]


for test_input in test_cases:
    result = normalizer.normalize(test_input)

    print("\n" + "=" * 60)
    print(f"Input   : {result['input']}")
    print(f"Skill   : {result['skill']}")
    print(f"Version : {result['version']}")
    print(f"Status  : {result['status']}")
    print("=" * 60)