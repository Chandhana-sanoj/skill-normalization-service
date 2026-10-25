"""Benchmark exact alias matching using the PostgreSQL catalogue."""

import statistics
import time

from app.repositories.canonical_skill_repository import CanonicalSkillRepository
from app.services.alias_matcher import AliasMatcher


def main():
    alias_map, canonical_map, _, _ = CanonicalSkillRepository().load_catalogue()
    matcher = AliasMatcher(alias_map=alias_map, canonical_map=canonical_map)

    test_inputs = [
        "Python",
        "Machine Learning",
        "SQL",
        "Python 3.12",
        "a skill that does not exist",
    ]

    for skill in test_inputs:
        matcher.match(skill)

    timings = []
    for _ in range(1000):
        for skill in test_inputs:
            start = time.perf_counter()
            matcher.match(skill)
            timings.append((time.perf_counter() - start) * 1000)

    print(f"Total measurements: {len(timings)}")
    print(f"Average latency: {statistics.mean(timings):.6f} ms")
    print(f"Median latency: {statistics.median(timings):.6f} ms")
    print(f"Minimum latency: {min(timings):.6f} ms")
    print(f"Maximum latency: {max(timings):.6f} ms")
    sorted_timings = sorted(timings)
    p95_index = int(0.95 * (len(sorted_timings) - 1))
    print(f"P95 latency: {sorted_timings[p95_index]:.6f} ms")


if __name__ == "__main__":
    main()