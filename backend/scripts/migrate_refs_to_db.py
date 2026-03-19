import shutil

from config import ASSETS_DIR, IMAGE_DIR
from database import SessionLocal
from models.character import Character


def migrate_references():
    db = SessionLocal()
    ref_dir = ASSETS_DIR / "references"
    stored_dir = IMAGE_DIR / "stored"
    stored_dir.mkdir(parents=True, exist_ok=True)

    print(f"🚀 Starting Migration: {ref_dir} -> Database & {stored_dir}")

    if not ref_dir.exists():
        print("❌ assets/references not found. Nothing to migrate.")
        return

    # 1. Iterate through files in assets/references
    for file_path in ref_dir.glob("*.png"):
        char_name = file_path.stem.replace("_", " ")  # Match DB format
        print(f"--- Processing: {char_name} ({file_path.name}) ---")

        # Find character in DB
        character = db.query(Character).filter(Character.name == char_name).first()

        if character:
            # New filename for stored directory
            new_filename = f"char_ref_{file_path.name}"
            target_path = stored_dir / new_filename

            # Copy file to stored directory
            shutil.copy2(file_path, target_path)

            # Update DB
            old_preview = character.preview_image_url
            character.preview_image_url = f"/outputs/images/stored/{new_filename}"

            print(f"✅ Migrated Character '{char_name}':")
            print(f"   - Old Preview: {old_preview}")
            print(f"   - New Preview: {character.preview_image_url}")
        else:
            print(f"⚠️ Character '{char_name}' not found in DB. Keeping as static asset for now.")

    db.commit()
    print("\n✨ Migration Complete. DB is now the source of truth for these characters.")
    db.close()


if __name__ == "__main__":
    migrate_references()
