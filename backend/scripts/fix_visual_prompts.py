import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models import Character

# Additional prompt fixes for preview quality (Thumbnails Phase)
UPDATES = {
    # Gunwoo & Sion - Faceless issue
    12: {
        "ref_append": ", highly detailed face, clear eyes, handsome facial features",
        "neg_append": ", faceless, blank face, no eyes",
    },
    16: {
        "ref_append": ", highly detailed face, clear eyes, cute facial features, smiling",
        "neg_append": ", faceless, blank face, no eyes",
    },
    # Sua & Jiho - Weird background issue
    15: {
        "ref_append": ", (simple white background:1.5)",
        "neg_append": ", complex background, objects in background, strange shapes, big circles, halos, abstract background",
    },
    14: {
        "ref_append": ", (simple white background:1.5)",
        "neg_append": ", complex background, objects in background, strange shapes, big rings, giant stones, abstract background",
    },
}

def main():
    db = SessionLocal()
    try:
        updated_count = 0
        for char_id, addons in UPDATES.items():
            char = db.query(Character).filter(Character.id == char_id).first()
            if char:
                # 1. Update reference_base_prompt
                if char.reference_base_prompt:
                    if "detailed face" not in char.reference_base_prompt and "simple white" not in char.reference_base_prompt:
                        char.reference_base_prompt += addons["ref_append"]
                else:
                    char.reference_base_prompt = char.custom_base_prompt + addons["ref_append"]

                # 2. Update custom_negative_prompt and reference_negative_prompt
                if char.custom_negative_prompt:
                    if addons["neg_append"].strip(", ") not in char.custom_negative_prompt:
                        char.custom_negative_prompt += addons["neg_append"]
                else:
                    char.custom_negative_prompt = "verybadimagenegative_v1.3" + addons["neg_append"]

                if char.reference_negative_prompt:
                    if addons["neg_append"].strip(", ") not in char.reference_negative_prompt:
                        char.reference_negative_prompt += addons["neg_append"]
                else:
                    char.reference_negative_prompt = "verybadimagenegative_v1.3" + addons["neg_append"]
                
                updated_count += 1
                print(f"✅ Appended Visual Fixes for '{char.name}' (ID: {char.id})")
            else:
                print(f"⚠️ Character ID {char_id} not found.")

        db.commit()
        print(f"\n🎉 Successfully appended visual fixes to {updated_count} character prompts.")
    except Exception as e:
        print(f"Error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
