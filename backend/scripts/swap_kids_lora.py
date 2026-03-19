import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models import Character

# LoRA Updates for Jiho and Subin
# We will switch them to ID 3 (chibi-laugh) or ID 6 (Gentle_Cubism_Light) which might look better than their current setups.
UPDATES = {
    # Jiho (14) - Switch to chibi-laugh (ID 3)
    14: [{"lora_id": 3, "weight": 0.65}],
    # Subin (13) - Switch to chibi-laugh (ID 3)
    13: [{"lora_id": 3, "weight": 0.65}],
}


def main():
    db = SessionLocal()
    try:
        updated_count = 0
        for char_id, new_loras in UPDATES.items():
            char = db.query(Character).filter(Character.id == char_id).first()
            if char:
                # Replace the entire loras JSON
                char.loras = new_loras
                updated_count += 1

                # Update their prompts slightly to fit the new Chibi style
                if "chibi" not in char.custom_base_prompt:
                    char.custom_base_prompt = "chibi style, cute cartoon, " + char.custom_base_prompt
                if "chibi" not in char.reference_base_prompt:
                    char.reference_base_prompt = "chibi style, cute cartoon, masterpiece, " + char.reference_base_prompt

                print(f"✅ Swapped LoRA to 'chibi-laugh' for '{char.name}' (ID: {char.id})")
            else:
                print(f"⚠️ Character ID {char_id} not found.")

        db.commit()
        print(f"\n🎉 Successfully updated {updated_count} character LoRAs.")
    except Exception as e:
        print(f"Error occurred: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
