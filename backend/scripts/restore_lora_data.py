
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm.attributes import flag_modified

from database import SessionLocal
from models.character import Character
from models.tag_alias import TagAlias


def restore_and_fix():
    db = SessionLocal()
    try:
        # 1. Fix Midoriya (Character)
        midoriya = db.query(Character).filter(Character.name == "Midoriya").first()
        if midoriya:
            # Check if LoRA exists in list
            current_loras = midoriya.loras or []
            if not any(entry.get('name') == 'mha_midoriya-10' for entry in current_loras):
                print("fixing Midoriya: adding mha_midoriya-10")
                current_loras.append({
                    "lora_id": 9, # from list_candidates
                    "name": "mha_midoriya-10",
                    "weight": 0.8,
                    "trigger_words": ["Midoriya_Izuku"],
                    "lora_type": "character"
                })
                midoriya.loras = current_loras
                flag_modified(midoriya, "loras")

        # 2. Fix Doremi (Character)
        doremi = db.query(Character).filter(Character.name == "Harukaze Doremi").first()
        if doremi:
             current_loras = doremi.loras or []
             if not any(entry.get('name') == 'harukaze-doremi-casual' for entry in current_loras):
                print("fixing Doremi: adding harukaze-doremi-casual")
                current_loras.append({
                    "lora_id": 7, # from list_candidates
                    "name": "harukaze-doremi-casual",
                    "weight": 0.8,
                    "trigger_words": ["doremi"],
                    "lora_type": "style"
                })
                doremi.loras = current_loras
                flag_modified(doremi, "loras")

        # 3. Restore Flat Color (Alias)
        # Check if exists
        fc_alias = db.query(TagAlias).filter(TagAlias.source_tag == "flat_color").first()
        if not fc_alias:
            print("Restoring flat_color alias")
            db.add(TagAlias(
                source_tag="flat_color",
                target_tag="flat_color, <lora:flat_color:0.8>",
                is_active=True
            ))

        # 4. Restore Geometric (Alias)
        geo_alias = db.query(TagAlias).filter(TagAlias.source_tag == "geometric").first()
        if not geo_alias:
            print("Restoring geometric alias")
            db.add(TagAlias(
                source_tag="geometric",
                target_tag="geometric, <lora:Gentle_Cubism_Light:0.8>",
                is_active=True
            ))

        # 5. Restore blindbox (Verify/Ensure)
        # blindbox alias was kept/updated to "BTM..." without lora, but character has lora.

        db.commit()
        print("✅ Restore complete.")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    restore_and_fix()
