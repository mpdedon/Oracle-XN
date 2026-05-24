"""Fix invalid enum values in the SEED_ITEMS += block of seed_data.py."""
path = "data/seed_data.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

marker = "SEED_ITEMS += ["
pos = src.index(marker)
before = src[:pos]
block = src[pos:]

replacements = [
    ('"price_tier": "economy"',    '"price_tier": "budget"'),
    ('"price_tier": "upper_mid"',  '"price_tier": "mid_range"'),
    ('"delivery_profile": "1-2_days"',   '"delivery_profile": "2-3_days"'),
    ('"delivery_profile": "3-5_days"',   '"delivery_profile": "one_week"'),
    ('"delivery_profile": "5-7_days"',   '"delivery_profile": "one_week"'),
    ('"delivery_profile": "7-14_days"',  '"delivery_profile": "one_week"'),
    ('"delivery_profile": "10-14_days"', '"delivery_profile": "one_week"'),
]

for old, new in replacements:
    count = block.count(old)
    block = block.replace(old, new)
    print(f"  {old!r}: {count} replaced")

with open(path, "w", encoding="utf-8") as f:
    f.write(before + block)

bad = [v for v in ["economy","upper_mid","1-2_days","3-5_days","5-7_days","7-14_days","10-14_days"] if v in block]
print("Remaining invalid values:", bad if bad else "None — all clean!")
