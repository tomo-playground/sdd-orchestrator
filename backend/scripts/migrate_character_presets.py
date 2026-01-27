#!/usr/bin/env python3
"""Migrate hardcoded CHARACTER_PRESETS from config.py to the database.

Usage:
    cd backend && uv run python scripts/migrate_character_presets.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from database import SessionLocal
from models.character import Character
from config import CHARACTER_PRESETS, logger

def migrate_presets():
    print("🚀 Starting IP-Adapter presets migration...")
    db = SessionLocal()
    try:
        # Get all characters from DB
        characters = db.query(Character).all()
        char_map = {c.name: c for t in [characters] for c in t}
        
        updated_count = 0
        for name, preset in CHARACTER_PRESETS.items():
            if name in char_map:
                char = char_map[name]
                print(f"  📦 Character found: {name}")
                
                # Update fields if they are currently null
                needs_update = False
                if char.ip_adapter_weight is None:
                    char.ip_adapter_weight = preset.get("weight")
                    needs_update = True
                    print(f"    - Set weight: {char.ip_adapter_weight}")
                
                if char.ip_adapter_model is None:
                    char.ip_adapter_model = preset.get("model")
                    needs_update = True
                    print(f"    - Set model: {char.ip_adapter_model}")
                
                if needs_update:
                    updated_count += 1
            else:
                print(f"  ⚠️  Character in config but not in DB: {name}")
        
        if updated_count > 0:
            db.commit()
            print(f"\n✅ Migration complete! {updated_count} characters updated.")
        else:
            print("\nℹ️ No updates needed. All characters already have settings or were not found.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_presets()
