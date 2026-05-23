import sys
sys.path.insert(0, ".")
from engine.memory_engine import BehaviouralMemoryEngine as ME

m = ME()
ids = m.list_all_user_ids()
p = m.get_profile(ids[0])
print("user_id:", p.user_id)
print("display_name:", p.display_name)
print("archetype:", p.archetype)
print("region:", p.region.value)
# Simulate demo line
label = p.archetype.replace("_", " ").title()
print("Demo label:", label)
