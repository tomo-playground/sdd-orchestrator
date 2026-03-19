from database import SessionLocal
from models.tag_alias import TagAlias


def register_chibi_rule():
    db = SessionLocal()
    try:
        source_tag = "chibi"
        # User said "chibi, laughing" are the triggers.
        # LoRA name is 'chibi-laugh' (confirmed from previous list).
        trigger_words = "chibi, laughing"
        lora_name = "chibi-laugh"

        target_tag = f"{trigger_words}, <lora:{lora_name}:0.8>"

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
        print("✅ Chibi rule registered successfully!")
        print(f"   Input: '{source_tag}'")
        print(f"   Result: '{target_tag}'")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    register_chibi_rule()
