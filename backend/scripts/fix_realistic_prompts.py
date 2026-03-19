import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models import Character

# Prompt updates for realistic characters
UPDATES = {
    # Yuna
    17: {
        "base": "1girl, 20s korean woman, beautiful, elegant, long wavy black hair, wearing elegant white silk blouse and black pencil skirt, delicate silver necklace, natural makeup, soft lighting, highly detailed realistic portrait",
        "negative": "nsfw, ugly, blurry, deformed, bad anatomy, bad hands, missing fingers, heavy makeup, cartoon, anime, illustration",
    },
    # Doyun
    18: {
        "base": "1boy, late 20s korean man, handsome, clean shaven, short straight black hair, sharp jawline, wearing tailored navy suit, crisp white shirt, minimalist watch, natural lighting, highly detailed realistic portrait",
        "negative": "nsfw, ugly, blurry, deformed, bad anatomy, bad hands, missing fingers, messy hair, casual clothes, cartoon, anime, illustration",
    },
}


def main():
    db = SessionLocal()
    try:
        updated_count = 0
        for char_id, prompts in UPDATES.items():
            char = db.query(Character).filter(Character.id == char_id).first()
            if char:
                # Append to existing ref base if missing descriptors
                char.custom_base_prompt = prompts["base"]
                char.custom_negative_prompt = prompts["negative"]
                updated_count += 1
                print(f"✅ Updated Appearance/Clothing Prompts for '{char.name}' (ID: {char.id})")
            else:
                print(f"⚠️ Character ID {char_id} not found.")

        db.commit()
        print(f"\n🎉 Successfully updated {updated_count} character prompts.")
    except Exception as e:
        print(f"Error occurred: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
