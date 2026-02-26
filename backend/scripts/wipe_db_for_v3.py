import os
import sys

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from database import engine


def wipe_data():
    """Wipes existing data from characters, scenes, and logs for a fresh V3 start."""
    print("🧹 Wiping existing data for a fresh V3 start...")

    tables_to_wipe = [
        "character_tags",
        "scene_tags",
        "scene_character_actions",
        "scenes",
        "characters",
        "activity_logs",
        "prompt_histories"
    ]

    # Allow-listed table names (validated against hardcoded set above)
    allowed_tables = set(tables_to_wipe)

    with engine.connect() as conn:
        # TRUNCATE CASCADE is cleaner in Postgres
        for table in tables_to_wipe:
            if table not in allowed_tables:
                print(f"   ❌ Skipping unknown table: {table}")
                continue
            try:
                # Table names are from hardcoded allow-list, safe for text()
                conn.execute(text("TRUNCATE TABLE " + table + " RESTART IDENTITY CASCADE"))
                print(f"   ✅ Cleaned {table}")
            except Exception as e:
                print(f"   ⚠️ Could not clean {table}: {e}")

        conn.commit()

    print("\n✨ Database is now clean and ready for V3 characters!")

if __name__ == "__main__":
    wipe_data()
