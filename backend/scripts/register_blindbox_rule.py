from database import SessionLocal
from models.tag_alias import TagAlias


def register_blindbox_rule():
    db = SessionLocal()
    try:
        source_tag = "blindbox"
        # User requested: "full body, chibi"
        # Known trigger for blindbox_v1_mix: "BTM" (from previous check)
        # We'll combine them for best effect.
        trigger_words = "BTM, full body, chibi"
        lora_name = "blindbox_v1_mix"

        target_tag = f"{trigger_words}, <lora:{lora_name}:0.8>"

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
        print("✅ Blindbox rule registered successfully!")
        print(f"   Input: '{source_tag}'")
        print(f"   Result: '{target_tag}'")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    register_blindbox_rule()
