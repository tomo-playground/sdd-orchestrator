"""Fill missing data for all characters based on Hana's structure."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import DEFAULT_REFERENCE_BASE_PROMPT, DEFAULT_REFERENCE_NEGATIVE_PROMPT, logger
from database import SessionLocal
from models import Character, CharacterTag, Tag


def main():
    db = SessionLocal()
    try:
        # Update Hana with complete data
        hana = db.query(Character).filter(Character.name == "Hana").first()
        if hana:
            hana.description = "Test character for - Generic anime girl with long hair and blue eyes"
            hana.recommended_negative = ["worst quality, low quality, lowres, bad anatomy"]
            hana.custom_base_prompt = "1girl, solo, long hair, blue eyes"
            hana.custom_negative_prompt = "worst quality, low quality, lowres, bad anatomy, bad hands"
            hana.reference_base_prompt = DEFAULT_REFERENCE_BASE_PROMPT + ", 1girl, long hair, blue eyes"
            hana.reference_negative_prompt = DEFAULT_REFERENCE_NEGATIVE_PROMPT
            logger.info("✅ Updated Hana with complete data")

        # Update Eureka
        eureka = db.query(Character).filter(Character.name == "Eureka").first()
        if eureka:
            # Add character tags for Eureka
            tags_to_add = [
                ("1girl", True, 1.0),
                ("solo", True, 1.0),
                ("purple_hair", True, 1.0),
                ("green_eyes", True, 1.0),
            ]

            for tag_name, is_permanent, weight in tags_to_add:
                tag = db.query(Tag).filter(Tag.name == tag_name).first()
                if not tag:
                    # Create tag if it doesn't exist
                    tag = Tag(name=tag_name, category="character", default_layer=0)
                    db.add(tag)
                    db.flush()

                # Check if tag is already linked
                existing = (
                    db.query(CharacterTag)
                    .filter(CharacterTag.character_id == eureka.id, CharacterTag.tag_id == tag.id)
                    .first()
                )

                if not existing:
                    char_tag = CharacterTag(
                        character_id=eureka.id, tag_id=tag.id, weight=weight, is_permanent=is_permanent
                    )
                    db.add(char_tag)

            logger.info("✅ Updated Eureka with character tags")

        # Update Midoriya
        midoriya = db.query(Character).filter(Character.name == "Midoriya").first()
        if midoriya:
            tags_to_add = [
                ("1boy", True, 1.0),
                ("solo", True, 1.0),
                ("green_hair", True, 1.0),
                ("green_eyes", True, 1.0),
            ]

            for tag_name, is_permanent, weight in tags_to_add:
                tag = db.query(Tag).filter(Tag.name == tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name, category="character", default_layer=0)
                    db.add(tag)
                    db.flush()

                existing = (
                    db.query(CharacterTag)
                    .filter(CharacterTag.character_id == midoriya.id, CharacterTag.tag_id == tag.id)
                    .first()
                )

                if not existing:
                    char_tag = CharacterTag(
                        character_id=midoriya.id, tag_id=tag.id, weight=weight, is_permanent=is_permanent
                    )
                    db.add(char_tag)

            logger.info("✅ Updated Midoriya with character tags")

        # Update Generic Anime Girl
        generic_girl = db.query(Character).filter(Character.name == "Generic Anime Girl").first()
        if generic_girl:
            tags_to_add = [
                ("1girl", True, 1.0),
                ("solo", True, 1.0),
            ]

            for tag_name, is_permanent, weight in tags_to_add:
                tag = db.query(Tag).filter(Tag.name == tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name, category="character", default_layer=0)
                    db.add(tag)
                    db.flush()

                existing = (
                    db.query(CharacterTag)
                    .filter(CharacterTag.character_id == generic_girl.id, CharacterTag.tag_id == tag.id)
                    .first()
                )

                if not existing:
                    char_tag = CharacterTag(
                        character_id=generic_girl.id, tag_id=tag.id, weight=weight, is_permanent=is_permanent
                    )
                    db.add(char_tag)

            logger.info("✅ Updated Generic Anime Girl with character tags")

        # Update Generic Anime Boy
        generic_boy = db.query(Character).filter(Character.name == "Generic Anime Boy").first()
        if generic_boy:
            tags_to_add = [
                ("1boy", True, 1.0),
                ("solo", True, 1.0),
            ]

            for tag_name, is_permanent, weight in tags_to_add:
                tag = db.query(Tag).filter(Tag.name == tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name, category="character", default_layer=0)
                    db.add(tag)
                    db.flush()

                existing = (
                    db.query(CharacterTag)
                    .filter(CharacterTag.character_id == generic_boy.id, CharacterTag.tag_id == tag.id)
                    .first()
                )

                if not existing:
                    char_tag = CharacterTag(
                        character_id=generic_boy.id, tag_id=tag.id, weight=weight, is_permanent=is_permanent
                    )
                    db.add(char_tag)

            logger.info("✅ Updated Generic Anime Boy with character tags")

        db.commit()
        logger.info("🎉 All characters updated successfully!")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error updating characters: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
