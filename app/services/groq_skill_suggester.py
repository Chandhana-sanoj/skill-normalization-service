

import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

ALLOWED_CATEGORIES = [
    "Creative & Media Skills",
    "Education & Training",
    "Engineering & Manufacturing",
    "Finance & Accounting",
    "Healthcare & Life Sciences",
    "Human Resources & Recruitment",
    "Legal, Risk & Compliance",
    "Management & Administration",
    "Marketing & Communications",
    "Operations & Supply Chain",
    "Project & Product Management",
    "Sales & Business Development",
    "Soft Skills & Professional Competencies",
    "Technology & Data",
]


class GroqSkillSuggester:
    """Generate validated skill suggestions using the Groq API."""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

        if not self.api_key:
            raise ValueError("GROQ_API_KEY is missing from environment.")

        self.timeout = httpx.Timeout(30.0, connect=10.0)

    def suggest(
        self,
        raw_skill: str,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:

        raw_skill = raw_skill.strip()

        if not raw_skill:
            raise ValueError("Raw skill cannot be empty.")

        if len(raw_skill) > 250:
            raise ValueError("Raw skill exceeds the maximum allowed length.")

        candidate_data = [
            {
                "name": str(candidate["name"]),
                "similarity": round(float(candidate["similarity"]), 4),
            }
            for candidate in candidates[:3]
            if candidate.get("name")
        ]

        messages = [
            {
                "role": "system",
                "content": """
You are a professional skill taxonomy and normalization engine.

Your task is to suggest a standardized skill entry for an existing
recruitment skill catalogue.

Rules:

1. Identify the actual skill represented by the raw input.
2. Use a concise, industry-standard canonical skill name.
3. Write a short catalogue-style description, ideally 2-6 words.
   Do not write full sentences or lengthy explanations.
4. Select exactly one category from the supplied allowed categories.

5. Generate aliases ONLY when they are genuine alternative names
   for the exact same skill.

6. Valid aliases include:
   - Common abbreviations (Python -> Py)
   - Established alternative names
   - Widely recognized equivalent naming conventions
   - Genuine spelling or naming variants

7. NEVER generate aliases that describe:
   - Activities performed using the skill
   - Applications or use cases of the skill
   - Related technologies
   - Subskills or specializations
   - Job roles or professional activities
   - Broader or narrower concepts

8. For example, if the canonical skill is Python:
   Valid aliases: ["Py"]
   Invalid aliases:
   ["Python scripting", "Python development",
    "Python coding", "Python software engineering",
    "Python programming"]

9. Do not include the canonical name itself as an alias.
10. Do not include proficiency levels such as beginner,
    intermediate, advanced, expert or professional.
11. Do not treat version numbers as separate skills unless
    the version represents a genuinely distinct technology.
12. Do not assume embedding candidates are correct.
13. If no genuine aliases exist, return an empty aliases list.
14. Never invent aliases just to fill the list.

15. Preserve the original competency's meaning. Do not replace
    a skill with a related but different competency merely because
    an embedding candidate has a higher similarity score.

16. For soft skills, distinguish between related competencies.
    Examples:
    - Working Under Pressure is not automatically Stress Management.
    - Adaptability is not automatically Resilience.
    - Leadership is not automatically Teamwork.
    - Communication is not automatically Active Listening.
    - Problem Solving is not automatically Critical Thinking.

17. Descriptions must be concise, grammatically complete
    noun phrases, ideally 2-6 words.

18. Use the category strings exactly as provided.
    Never modify spelling, spacing, punctuation or capitalization.


Canonical naming principles:

- Correct misspellings, informal names, abbreviations and
  non-standard inputs to their established canonical skill names.
- Preserve an input when it is already a valid, recognized,
  specific industry-standard skill name.
- Do not replace a valid specific skill with a broader,
  narrower or merely related concept.
- Do not assume that a technically related term is an equivalent
  canonical name.
- Use embedding candidates as supporting context, not as
  instructions to rename the skill.
- Prefer the most widely recognized industry-standard name
  when multiple genuine equivalent names exist.

Return valid JSON with exactly these fields:
{
  "name": "Canonical skill name",
  "description": "Concise skill description",
  "category": "One allowed category",
  "aliases": ["Alias 1", "Alias 2"]
}

Return JSON only.
""",
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "raw_skill": raw_skill,
                        "embedding_candidates": candidate_data,
                        "allowed_categories": ALLOWED_CATEGORIES,
                    },
                    ensure_ascii=False,
                ),
            },
        ]

        try:
            response = httpx.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                },
                timeout=self.timeout,
            )

            response.raise_for_status()

            content = response.json()["choices"][0]["message"]["content"]

            if not content:
                raise ValueError("Groq returned an empty response.")

            suggestion = json.loads(content)

            return self._validate_suggestion(suggestion)

        except httpx.TimeoutException as exc:
            raise RuntimeError("Groq API request timed out.") from exc

        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Groq API returned HTTP {exc.response.status_code}: "
                f"{exc.response.text[:500]}"
            ) from exc

        except httpx.RequestError as exc:
            raise RuntimeError(f"Groq API connection failed: {exc}") from exc

        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                "Groq returned an invalid response format."
            ) from exc

    @staticmethod
    def _validate_suggestion(data: dict) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise ValueError("Suggestion must be a JSON object.")

        required_fields = {"name", "description", "category", "aliases"}

        if set(data.keys()) != required_fields:
            raise ValueError("Suggestion contains missing or unexpected fields.")

        name = data["name"]
        description = data["description"]
        category = data["category"]
        aliases = data["aliases"]

        if not all(isinstance(value, str) for value in [name, description, category]):
            raise ValueError("Name, description and category must be strings.")

        name = name.strip()
        description = description.strip()
        category = category.strip()

        if not name or len(name) > 150:
            raise ValueError("Invalid canonical skill name.")

        if not description or len(description) > 500:
            raise ValueError("Invalid skill description.")

        if category not in ALLOWED_CATEGORIES:
            raise ValueError(f"Invalid skill category: {category}")

        if not isinstance(aliases, list):
            raise ValueError("Aliases must be a list.")

        if len(aliases) > 8:
            raise ValueError("Maximum of 8 aliases allowed.")

        cleaned_aliases = []
        seen = {name.casefold()}

        for alias in aliases:
            if not isinstance(alias, str):
                continue

            alias = alias.strip()

            if not alias or len(alias) > 150:
                continue

            if alias.casefold() in seen:
                continue

            seen.add(alias.casefold())
            cleaned_aliases.append(alias)

        return {
            "name": name,
            "description": description,
            "category": category,
            "aliases": cleaned_aliases,
        }
