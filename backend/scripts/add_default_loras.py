#!/usr/bin/env python3
"""Add default LoRAs used in this project.

Usage:
    cd backend && uv run python scripts/add_default_loras.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from database import SessionLocal
from models import LoRA

# Default LoRAs based on ROADMAP.md
DEFAULT_LORAS = [
    {
        "name": "eureka_v9",
        "display_name": "Eureka V9",
        "trigger_words": ["eureka"],
        "default_weight": 1.0,
        "weight_min": 0.5,
        "weight_max": 1.5,
        "base_models": ["animagine-xl"],
        "character_defaults": {
            "hair_color": "aqua_hair",
            "eye_color": "purple_eyes",
            "hair_style": "short_hair",
        },
        "recommended_negative": ["verybadimagenegative_v1.3"],
    },
    {
        "name": "chibi-laugh",
        "display_name": "Chibi Laugh",
        "trigger_words": ["chibi", "eyebrow", "laughing", "eyebrow down"],
        "default_weight": 0.6,
        "weight_min": 0.3,
        "weight_max": 0.8,
        "base_models": ["*"],  # Works with any model
        "recommended_negative": ["easynegative"],
    },
]


def add_default_loras(db: Session) -> tuple[int, int]:
    """Add default LoRAs. Returns (added, skipped) count."""
    added = 0
    skipped = 0

    for lora_data in DEFAULT_LORAS:
        existing = db.query(LoRA).filter(LoRA.name == lora_data["name"]).first()
        if existing:
            skipped += 1
            print(f"  ⏭️  Skipped (exists): {lora_data['name']}")
            continue

        lora = LoRA(**lora_data)
        db.add(lora)
        added += 1
        print(f"  ✅ Added: {lora_data['name']}")

    return added, skipped


def main():
    """Main function."""
    print("🚀 Adding default LoRAs...")

    db = SessionLocal()
    try:
        added, skipped = add_default_loras(db)
        db.commit()
        print(f"\n🎉 Done! Added: {added}, Skipped: {skipped}")
    except Exception as e:
        db.rollback()
        print(f"❌ Failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
