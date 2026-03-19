from config import logger
from database import SessionLocal
from models import Tag


def upsert_tags():
    db = SessionLocal()
    try:
        tag_data = [
            {"name": "doremi", "category": "identity", "group_name": "identity"},
            {"name": "casual_outfit", "category": "character", "group_name": "clothing"},
            {"name": "soft_light", "category": "quality", "group_name": "lighting"},
            {"name": "sun", "category": "environment", "group_name": "time_weather"},
            {"name": "day", "category": "time_weather", "group_name": "time_weather"},
            {"name": "beckoning", "category": "action", "group_name": "pose"},
        ]

        for data in tag_data:
            tag = db.query(Tag).filter(Tag.name == data["name"]).first()
            if not tag:
                logger.info(f"Creating tag: {data['name']} -> {data['group_name']}")
                tag = Tag(
                    name=data["name"],
                    category=data["category"],
                    group_name=data["group_name"],
                    classification_source="manual_fix",
                    classification_confidence=1.0,
                )
                db.add(tag)
            else:
                logger.info(f"Updating tag: {data['name']} -> {data['group_name']}")
                tag.category = data["category"]
                tag.group_name = data["group_name"]
                tag.classification_confidence = 1.0

        db.commit()
        logger.info("✅ All requested tags upserted/updated.")
    except Exception as e:
        logger.error(f"Failed to upsert tags: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    upsert_tags()
