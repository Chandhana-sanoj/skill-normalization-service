from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# Load model
model = SentenceTransformer("sentence-transformers/all-MiniLM-L12-v2")


# Canonical skills
skills = [
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "C++",
    "C#",
    "React",
    "React Native",
    "Angular",
    "Vue.js",
    "SQL",
    "PostgreSQL",
    "MySQL",
    "MongoDB",
    "Kubernetes",
]


# Test inputs and their expected canonical skill
test_cases = [
    # Programming languages
    ("Python", "Python"),
    ("py", "Python"),
    ("Python programming", "Python"),
    ("Python scripting language", "Python"),

    ("Java", "Java"),
    ("Java language", "Java"),
    ("Java programming", "Java"),

    ("JavaScript", "JavaScript"),
    ("JS", "JavaScript"),
    ("ECMAScript", "JavaScript"),
    ("JavaScript programming", "JavaScript"),

    ("TypeScript", "TypeScript"),
    ("TS", "TypeScript"),

    ("C++", "C++"),
    ("cpp", "C++"),

    ("C#", "C#"),
    ("c sharp", "C#"),
    ("C sharp programming", "C#"),

    # Frontend
    ("React", "React"),
    ("ReactJS", "React"),
    ("React library", "React"),

    ("React Native", "React Native"),
    ("ReactNative", "React Native"),
    ("React Native framework", "React Native"),

    ("Angular", "Angular"),
    ("AngularJS", "Angular"),

    ("Vue", "Vue.js"),
    ("VueJS", "Vue.js"),

    # Databases
    ("SQL", "SQL"),
    ("Structured Query Language", "SQL"),
    ("SQL language", "SQL"),

    ("PostgreSQL", "PostgreSQL"),
    ("Postgres", "PostgreSQL"),
    ("Postgres database", "PostgreSQL"),

    ("MySQL", "MySQL"),
    ("MySQL database", "MySQL"),

    ("MongoDB", "MongoDB"),
    ("Mongo DB", "MongoDB"),

    # Kubernetes
    ("K8s", "Kubernetes"),
    ("Kubernetes", "Kubernetes"),
    ("Kubernetes platform", "Kubernetes"),
]


# Generate embeddings for canonical skills
skill_embeddings = model.encode(skills)


top1_correct = 0
top3_correct = 0


print("=" * 70)
print("MODEL: all-MiniLM-L12-v2")
print("=" * 70)


for test_input, expected in test_cases:

    # Generate embedding for input
    input_embedding = model.encode([test_input])

    # Calculate similarity
    scores = cosine_similarity(
        input_embedding,
        skill_embeddings
    )[0]

    # Rank skills by similarity
    ranked_indices = scores.argsort()[::-1]

    top1 = skills[ranked_indices[0]]
    top3 = [skills[i] for i in ranked_indices[:3]]

    # Check accuracy
    if top1 == expected:
        top1_correct += 1

    if expected in top3:
        top3_correct += 1

    print(f"\nInput:    {test_input}")
    print(f"Expected: {expected}")
    print(f"Top 1:    {top1}")
    print(f"Top 3:    {top3}")


# Calculate accuracy
total = len(test_cases)

top1_accuracy = (top1_correct / total) * 100
top3_accuracy = (top3_correct / total) * 100


print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)

print(f"Total test cases : {total}")
print(f"Top-1 correct    : {top1_correct}")
print(f"Top-3 correct    : {top3_correct}")
print(f"Top-1 accuracy   : {top1_accuracy:.2f}%")
print(f"Top-3 accuracy   : {top3_accuracy:.2f}%")