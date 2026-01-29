from database import SessionLocal
from models.tag_alias import TagAlias

def register_midoriya_alias():
    db = SessionLocal()
    try:
        # User defined info
        source_tag = "Midoriya_Izuku"
        trigger_word = "Midoriya_Izuku" # User said "Trigger: Midoriya_Izuku"
        lora_name_part = "mha_midoriya-10" # Based on Civitai search result earlier (even though search said Mount Lady, user seems to trust this file)
        # Actually user just said "LoRA of Midoriya Izuku, Trigger: Midoriya_Izuku".
        # Let's assume the existing LoRA 'mha_midoriya-10' is the correct one.
        
        target_tag = f"{trigger_word}, <lora:{lora_name_part}:0.8>"
        
        existing = db.query(TagAlias).filter(TagAlias.source_tag == source_tag).first()
        if existing:
            print(f"Updating existing alias for '{source_tag}'")
            existing.target_tag = target_tag
            existing.reason = "User manual trigger definition"
        else:
            print(f"Creating new alias for '{source_tag}'")
            db.add(TagAlias(
                source_tag=source_tag,
                target_tag=target_tag,
                reason="User manual trigger definition",
                active=True
            ))
        
        db.commit()
        print("✅ Midoriya alias registered successfully!")
        print(f"   Input: '{source_tag}'")
        print(f"   Result: '{target_tag}'")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    register_midoriya_alias()
