
from config import logger
from database import SessionLocal
from models import Tag


def fix_misclassified_tags():
    db = SessionLocal()
    try:
        # 1. Update 'sun' to 'time_weather'
        sun = db.query(Tag).filter(Tag.name == "sun").first()
        if sun:
            logger.info(f"Updating 'sun': {sun.group_name} -> time_weather")
            sun.category = "scene"
            sun.group_name = "time_weather"

        # 2. Add 'soft_light' as 'lighting'
        soft_light = db.query(Tag).filter(Tag.name == "soft_light").first()
        if not soft_light:
            logger.info("Creating 'soft_light' tag")
            soft_light = Tag(
                name="soft_light",
                category="quality", # lighting often considered quality/style or environment
                group_name="lighting",
                default_layer=0, # Meta/Global
                usage_scope="ANY"
            )
            db.add(soft_light)
        else:
             logger.info(f"Updating 'soft_light': {soft_light.group_name} -> lighting")
             soft_light.group_name = "lighting"

        # 3. Add 'beckoning' as 'pose' or 'action'
        beckoning = db.query(Tag).filter(Tag.name == "beckoning").first()
        if not beckoning:
            logger.info("Creating 'beckoning' tag")
            beckoning = Tag(
                name="beckoning",
                category="scene",
                group_name="pose", # PromptPreview maps 'pose' and 'action' similarly, but 'pose' is usually static
                default_layer=5, # Pose layer
                usage_scope="TRANSIENT"
            )
            db.add(beckoning)
        else:
             logger.info(f"Updating 'beckoning': {beckoning.group_name} -> pose")
             beckoning.group_name = "pose"

        # 4. Check 'anime' (often 'skip')
        anime = db.query(Tag).filter(Tag.name == "anime").first()
        if anime:
             # Make sure it's style
             anime.group_name = "style"

        db.commit()
        logger.info("✅ Tag classification fixes applied.")

    except Exception as e:
        logger.error(f"Failed to fix tags: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_misclassified_tags()
