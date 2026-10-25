"""Print alias conflicts found in the PostgreSQL skill catalogue."""

from app.repositories.canonical_skill_repository import CanonicalSkillRepository


alias_map, canonical_map, _, _ = CanonicalSkillRepository().load_catalogue()
conflicts = {
    alias: sorted(ids)
    for alias, ids in alias_map.items()
    if len(ids) > 1
}

print(f"Total conflicting aliases: {len(conflicts)}")
for alias, ids in sorted(conflicts.items()):
    print(f"\\nALIAS: {alias}")
    for skill_id in ids:
        print(f"  {skill_id}: {canonical_map.get(skill_id, 'UNKNOWN')}")
