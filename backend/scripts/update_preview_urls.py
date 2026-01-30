"""Update characters with existing reference images from assets/references."""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import logger
from database import SessionLocal
from models import Character


def main():
    db = SessionLocal()
    try:
        # Map character names to reference image filenames
        reference_mapping = {
            "Eureka": "Eureka.png",
            "Midoriya": "Midoriya.png",
            "Generic Anime Girl": "Generic Anime Girl.png",
            "Generic Anime Boy": "Generic Anime Boy.png",
        }

        for char_name, filename in reference_mapping.items():
            character = db.query(Character).filter(Character.name == char_name).first()
            if character:
                # Update preview_image_url to point to the reference image
                character.preview_image_url = f"/assets/references/{filename}"
                logger.info(f"✅ Updated {char_name}: {character.preview_image_url}")

        db.commit()
        logger.info("🎉 All character preview URLs updated!")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error updating preview URLs: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
