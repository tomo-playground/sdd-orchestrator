import sys
import os

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

def wipe_data():
    """Wipes existing data from characters, scenes, and logs for a fresh V3 start."""
    print("🧹 Wiping existing data for a fresh V3 start...")
    
    tables_to_wipe = [
        "character_tags",
        "scene_tags",
        "scene_character_actions",
        "scenes",
        "characters",
        "generation_logs",
        "prompt_histories"
    ]
    
    with engine.connect() as conn:
        # Disable foreign key checks temporarily if needed, 
        # but TRUNCATE CASCADE is cleaner in Postgres
        for table in tables_to_wipe:
            try:
                conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
                print(f"   ✅ Cleaned {table}")
            except Exception as e:
                print(f"   ⚠️ Could not clean {table}: {e}")
        
        conn.commit()
    
    print("\n✨ Database is now clean and ready for V3 characters!")

if __name__ == "__main__":
    wipe_data()
