"""Add archetype column to user_profiles table if missing."""
import sqlite3
import sys
sys.path.insert(0, ".")

con = sqlite3.connect("oracle_xn.db")
cur = con.cursor()
cols = [row[1] for row in cur.execute("PRAGMA table_info(user_profiles)").fetchall()]
print("Existing columns:", cols)
if "archetype" not in cols:
    cur.execute("ALTER TABLE user_profiles ADD COLUMN archetype TEXT NOT NULL DEFAULT 'value_hunter'")
    con.commit()
    print("Column 'archetype' added successfully.")
else:
    print("Column 'archetype' already exists.")
con.close()
