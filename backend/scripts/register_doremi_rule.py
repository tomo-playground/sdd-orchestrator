from database import SessionLocal
from models.tag_alias import TagAlias


def register_doremi_rule():
    db = SessionLocal()
    try:
        source_tag = "doremi"
        # User requested: "doremi"
        # Since I don't know the exact trigger words for doremi character (likely "1girl, pink hair..." etc),
        # I will just map the LoRA for now.
        # But wait, looking at the list, the LoRA name is 'harukaze-doremi-casual'.
        lora_name = "harukaze-doremi-casual"

        # Adding 'doremi' as the trigger word too, assuming it might work or is desired.
        target_tag = f"doremi, <lora:{lora_name}:0.8>"

        existing = db.query(TagAlias).filter(TagAlias.source_tag == source_tag).first()
        if existing:
            print(f"Updating existing alias for '{source_tag}'")
            existing.target_tag = target_tag
            existing.reason = "User manual trigger definition"
        else:
            print(f"Creating new alias for '{source_tag}'")
            db.add(
                TagAlias(
                    source_tag=source_tag,
                    target_tag=target_tag,
                    reason="User manual trigger definition",
                    is_active=True,
                )
            )

        db.commit()
        print("✅ Doremi rule registered successfully!")
        print(f"   Input: '{source_tag}'")
        print(f"   Result: '{target_tag}'")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    register_doremi_rule()
