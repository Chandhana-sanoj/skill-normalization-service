from app.repositories.canonical_skill_repository import (
    CanonicalSkillRepository,
)
from app.services.normalizer import SkillNormalizer
from app.services.vector_search import VectorSearcher


CATALOGUE_FILE = "skill_catalogue.xlsx"


catalogue_repository = CanonicalSkillRepository()

alias_map, canonical_map, description_map = (
    catalogue_repository.load_catalogue()
)
vector_searcher = VectorSearcher()

normalizer = SkillNormalizer(
    alias_map=alias_map,
    canonical_map=canonical_map,
    vector_searcher=vector_searcher,
    organization_id=1,
    description_map=description_map,
)


test_cases = [
    # 1. Exact matching
    "Python",
    "Java",
    "Waste Management",

    # 2. Alias matching
    "Py",
    "Office 365",
    "ES6",

    # 3. Version extraction
    "Python 3.10",
    "Python 3.12",
    "Java 17",
    "Node.js 20",
    "Python 2.7",
    "Java 8",

    # 4. Skill names that contain numbers
    # These should NOT have a version extracted
    "Web3",
    "Office 365",
    "3D Modeling",
    "ES6",
    "HTML5",
    "CSS3",
    "Python3",
    "GPT-4o",
    "S3",
    "Log4j",

    # 5. Punctuation-sensitive skills
    "C++",
    "C#",
    ".NET",
    "Node.js",
    "F#",
    "Objective-C",
    "CI/CD",

    # 6. Case variations
    "python",
    "PYTHON",
    "PyThOn",
    "PythOn programming",
    "c++",
    "c#",
    "node.js",

    # 7. Whitespace variations
    "  Python  ",
    "  C++ ",
    "Node.js   ",
    "Python   3.10",
    "Java  17",

    # 8. Semantic matching
    "management of waste",
    "managing cloud infrastructure",
    "handling cloud systems",
    "data analysis using spreadsheets",
    "building websites",
    "wastewater treatment",

    # 9. Related skills that should not automatically
    # be treated as the same skill
    "Cloud Security",
    "Cloud Infrastructure",
    "Machine Learning",
    "Deep Learning",
    "Data Analysis",
    "Data Engineering",

    # 10. Unknown skills
    "SomeCompletelyUnknownSkill",
    "UnknownSkill 9.2",
    "RandomSkillXYZ123",

    # 11. Empty or unusual inputs
    "",
    "   ",
]

for test_input in test_cases:
    result = normalizer.normalize(test_input)

    print("\n" + "=" * 60)
    print(f"Input   : {result['input']}")
    print(f"Skill   : {result['skill']}")
    print(f"Version : {result['version']}")
    print(f"Description : {result.get('description')}")
    print(f"Status  : {result['status']}")
    print("=" * 60)
    