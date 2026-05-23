"""Diversify user archetypes and Nigerian regions using raw SQLite."""
import sqlite3
import random

ARCHETYPE_WEIGHTS = [
    ("value_hunter", 0.18),
    ("prestige_seeker", 0.12),
    ("social_buyer", 0.13),
    ("practical_buyer", 0.13),
    ("impulse_buyer", 0.10),
    ("quality_seeker", 0.11),
    ("deal_hunter", 0.11),
    ("loyalist", 0.12),
]

REGION_WEIGHTS = [
    ("Lagos", 0.30),
    ("Abuja", 0.20),
    ("Kano", 0.15),
    ("Port Harcourt", 0.11),
    ("Ibadan", 0.09),
    ("Enugu", 0.08),
    ("Benin City", 0.07),
]

archetypes = [a for a, _ in ARCHETYPE_WEIGHTS]
arch_probs = [p for _, p in ARCHETYPE_WEIGHTS]
regions = [r for r, _ in REGION_WEIGHTS]
region_probs = [p for _, p in REGION_WEIGHTS]

random.seed(42)

con = sqlite3.connect("oracle_xn.db")
cur = con.cursor()

user_ids = [row[0] for row in cur.execute("SELECT user_id FROM user_profiles").fetchall()]
print(f"Updating {len(user_ids)} users with diverse archetypes and regions...")

for uid in user_ids:
    arch = random.choices(archetypes, weights=arch_probs, k=1)[0]
    reg = random.choices(regions, weights=region_probs, k=1)[0]
    cur.execute(
        "UPDATE user_profiles SET archetype=?, region=? WHERE user_id=?",
        (arch, reg, uid),
    )

con.commit()
print("Done. Distribution:")

print("\nArchetypes:")
for arch, cnt in sorted(
    cur.execute("SELECT archetype, COUNT(*) FROM user_profiles GROUP BY archetype").fetchall(),
    key=lambda x: -x[1],
):
    print(f"  {arch:20s}  {cnt}")

print("\nRegions:")
for reg, cnt in sorted(
    cur.execute("SELECT region, COUNT(*) FROM user_profiles GROUP BY region").fetchall(),
    key=lambda x: -x[1],
):
    print(f"  {reg:20s}  {cnt}")

con.close()
