from pathlib import Path
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOGUE_PATH = PROJECT_ROOT / "skill_catalogue.xlsx"

MODELS = [
    "BAAI/bge-small-en-v1.5",
    "BAAI/bge-base-en-v1.5",
    "all-MiniLM-L6-v2",
]

# Small controlled semantic test set.
# Expected Canonical MUST exist in the real catalogue.
TEST_CASES = [
    # -------------------------
    # Python
    # -------------------------
    ("Python 3", "Python"),
    ("Python 3.10", "Python"),
    ("Python3", "Python"),
    ("Python 3.12", "Python"),

    # -------------------------
    # Java
    # -------------------------
    ("Java 8", "Java"),
    ("Java 11", "Java"),
    ("Java 17", "Java"),
    ("Java 21", "Java"),

    # -------------------------
    # JavaScript
    # -------------------------
    ("JS", "JavaScript"),
    ("JS ES6", "JavaScript"),
    ("ECMAScript", "JavaScript"),
    ("ECMAScript 6", "JavaScript"),
    ("JavaScript ES6", "JavaScript"),

    # -------------------------
    # TypeScript
    # -------------------------
    ("TS", "TypeScript"),
    ("TypeScript 4", "TypeScript"),
    ("TypeScript 5", "TypeScript"),
    ("TS 5.0", "TypeScript"),

    # -------------------------
    # C++
    # -------------------------
    ("CPP", "C++"),
    ("C plus plus", "C++"),
    ("C++ 11", "C++"),
    ("C++17", "C++"),
    ("C++ 20", "C++"),

    # -------------------------
    # C#
    # -------------------------
    ("C sharp", "C#"),
    ("C Sharp", "C#"),
    ("CSharp", "C#"),
    ("C# 10", "C#"),
    ("C# 12", "C#"),

    # -------------------------
    # React
    # -------------------------
    ("ReactJS", "React"),
    ("React.js", "React"),
    ("React 17", "React"),
    ("React 18", "React"),
    ("React 19", "React"),

    # -------------------------
    # React Native
    # -------------------------
    ("ReactNative", "React Native"),
    ("React Native 0.70", "React Native"),
    ("React Native 0.72", "React Native"),
    ("React Native 0.73", "React Native"),
    ("ReactNative 0.74", "React Native"),

    # -------------------------
    # Angular
    # -------------------------
    ("AngularJS", "Angular"),
    ("Angular 14", "Angular"),
    ("Angular 16", "Angular"),
    ("Angular 17", "Angular"),
    ("Angular 18", "Angular"),

    # -------------------------
    # Vue
    # -------------------------
    ("Vue", "Vue.js"),
    ("VueJS", "Vue.js"),
    ("Vue.js 2", "Vue.js"),
    ("Vue.js 3", "Vue.js"),

    # -------------------------
    # Node.js
    # -------------------------
    ("NodeJS", "Node.js"),
    ("Node.js 18", "Node.js"),
    ("Node.js 20", "Node.js"),
    ("Node 22", "Node.js"),

    # -------------------------
    # .NET
    # -------------------------
    (".NET 6", ".NET"),
    (".NET 7", ".NET"),
    (".NET 8", ".NET"),
    ("DotNet", ".NET"),

    # -------------------------
    # ASP.NET
    # -------------------------
    ("ASP.NET Core", "ASP.NET"),
    ("ASP.NET 6", "ASP.NET"),
    ("ASP.NET 8", "ASP.NET"),

    # -------------------------
    # Databases
    # -------------------------
    ("Postgres", "PostgreSQL"),
    ("PostgreSQL 12", "PostgreSQL"),
    ("PostgreSQL 15", "PostgreSQL"),
    ("Postgres 16", "PostgreSQL"),

    ("MySQL 5.7", "MySQL"),
    ("MySQL 8", "MySQL"),
    ("MySQL 8.0", "MySQL"),

    ("Mongo DB", "MongoDB"),
    ("MongoDB 5", "MongoDB"),
    ("MongoDB 7", "MongoDB"),

    ("MS SQL", "Microsoft SQL Server"),
    ("MSSQL", "Microsoft SQL Server"),
    ("SQL Server 2019", "Microsoft SQL Server"),
    ("SQL Server 2022", "Microsoft SQL Server"),

    # -------------------------
    # Cloud
    # -------------------------
    ("AWS", "Amazon Web Services"),
    ("Amazon AWS", "Amazon Web Services"),
    ("AWS Cloud", "Amazon Web Services"),

    ("Azure", "Microsoft Azure"),
    ("Microsoft Azure Cloud", "Microsoft Azure"),

    ("GCP", "Google Cloud"),
    ("Google Cloud Platform", "Google Cloud"),

    # -------------------------
    # DevOps
    # -------------------------
    ("K8s", "Kubernetes"),
    ("K8s 1.28", "Kubernetes"),
    ("Kubernetes 1.29", "Kubernetes"),
    ("Kubernetes 1.30", "Kubernetes"),

    ("Docker 20", "Docker"),
    ("Docker 24", "Docker"),
    ("Docker 25", "Docker"),

    ("Terraform 1.5", "Terraform"),
    ("Terraform 1.6", "Terraform"),
    ("Terraform 1.9", "Terraform"),

    # -------------------------
    # Python libraries
    # -------------------------
    ("Pandas 1.5", "Pandas"),
    ("Pandas 2", "Pandas"),
    ("NumPy 1.24", "NumPy"),
    ("NumPy 2", "NumPy"),

    ("PyTorch 2", "PyTorch"),
    ("TensorFlow 2", "TensorFlow"),
    ("Keras 3", "Keras"),
    ("Scikit Learn", "Scikit-learn"),
    ("Sklearn", "Scikit-learn"),

    # -------------------------
    # APIs / tools
    # -------------------------
    ("REST APIs", "REST API"),
    ("RESTful API", "REST API"),
    ("GraphQL API", "GraphQL"),
    ("Postman API testing", "Postman"),

    # -------------------------
    # Testing
    # -------------------------
    ("PyTest", "PyTest"),
    ("pytest", "PyTest"),
    ("JUnit 4", "JUnit"),
    ("JUnit 5", "JUnit"),
    ("Selenium WebDriver", "Selenium"),

    # -------------------------
    # Data / BI
    # -------------------------
    ("PowerBI", "Power BI"),
    ("Power BI Desktop", "Power BI"),
    ("Excel", "Microsoft Excel"),
    ("MS Excel", "Microsoft Excel"),

    # -------------------------
    # Git
    # -------------------------
    ("Git SCM", "Git"),
    ("GitHub", "GitHub"),
    ("GitLab", "GitLab"),
]


# -----------------------------
# Load actual catalogue
# -----------------------------

df = pd.read_excel(CATALOGUE_PATH)

canonical_names = (
    df["Canonical Name"]
    .dropna()
    .astype(str)
    .str.strip()
    .drop_duplicates()
    .tolist()
)

print(f"Loaded {len(canonical_names)} canonical skills.")

catalogue_set = set(canonical_names)

# Make sure every expected answer exists.
for _, expected in TEST_CASES:
    if expected not in catalogue_set:
        raise ValueError(
            f"Expected skill not found in catalogue: {expected}"
        )


# -----------------------------
# Run each model
# -----------------------------

summary = []

for model_name in MODELS:

    print("\n" + "=" * 70)
    print(model_name)
    print("=" * 70)

    model = SentenceTransformer(model_name)

    # ONLY canonical names are embedded.
    print("Embedding catalogue...")

    catalogue_embeddings = model.encode(
        canonical_names,
        normalize_embeddings=True,
        show_progress_bar=True,
        batch_size=64,
    )

    test_inputs = [x[0] for x in TEST_CASES]

    print("Embedding test inputs...")

    test_embeddings = model.encode(
        test_inputs,
        normalize_embeddings=True,
        show_progress_bar=True,
        batch_size=64,
    )

    similarities = cosine_similarity(
        test_embeddings,
        catalogue_embeddings
    )

    top1 = 0
    top3 = 0
    top5 = 0

    for i, (_, expected) in enumerate(TEST_CASES):

        ranked = np.argsort(similarities[i])[::-1]

        top1_skill = canonical_names[ranked[0]]
        top3_skills = [canonical_names[x] for x in ranked[:3]]
        top5_skills = [canonical_names[x] for x in ranked[:5]]

        if top1_skill == expected:
            top1 += 1

        if expected in top3_skills:
            top3 += 1

        if expected in top5_skills:
            top5 += 1

        print(
            f"{test_inputs[i]:45} -> "
            f"{top1_skill:30} "
            f"{'✓' if top1_skill == expected else '✗'}"
        )

    total = len(TEST_CASES)

    result = {
        "Model": model_name,
        "Test Cases": total,
        "Top-1": round(top1 / total * 100, 2),
        "Top-3": round(top3 / total * 100, 2),
        "Top-5": round(top5 / total * 100, 2),
    }

    summary.append(result)

    print("\nResults:")
    print(f"Top-1: {result['Top-1']}%")
    print(f"Top-3: {result['Top-3']}%")
    print(f"Top-5: {result['Top-5']}%")


# -----------------------------
# Final comparison
# -----------------------------

results = pd.DataFrame(summary)

print("\n" + "=" * 70)
print("MODEL COMPARISON")
print("=" * 70)

print(results.to_string(index=False))

results.to_csv(
    PROJECT_ROOT / "catalogue_benchmark" / "model_comparison.csv",
    index=False
)

print("\nSaved: catalogue_benchmark/model_comparison.csv")