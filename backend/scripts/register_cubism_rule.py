from database import SessionLocal
from models.tag_alias import TagAlias


def register_cubism_rule():
    db = SessionLocal()
    try:
        source_tag = "geometric"
        # User requested: "Gentle_Cubism_Light -> geometric"
        # So inputting 'geometric' triggers the LoRA.
        lora_name = "Gentle_Cubism_Light"

        # We append the LoRA syntax to the user's keyword.
        target_tag = f"{source_tag}, <lora:{lora_name}:0.8>"

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
                is_active=True
            ))

        db.commit()
        print("✅ Cubism role registered successfully!")
        print(f"   Input: '{source_tag}'")
        print(f"   Result: '{target_tag}'")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    register_cubism_rule()
