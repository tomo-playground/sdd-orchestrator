"""Force fix all character preview URLs to be relative and fix Eureka's identity tags."""

from database import SessionLocal
from models import Character, CharacterTag, Tag


def main():
    db = SessionLocal()
    try:
        # 1. Force relative URLs for all characters
        characters = db.query(Character).all()
        print(f"Fixing URLs for {len(characters)} characters...")
        for char in characters:
            if char.preview_image_url and "http" in char.preview_image_url:
                # Extract path after the domain
                old_url = char.preview_image_url
                if "/outputs/" in old_url:
                    char.preview_image_url = "/outputs/" + old_url.split("/outputs/")[-1]
                    print(f"  {char.name}: {old_url} -> {char.preview_image_url}")
                elif "/assets/" in old_url:
                    char.preview_image_url = "/assets/" + old_url.split("/assets/")[-1]
                    print(f"  {char.name}: {old_url} -> {char.preview_image_url}")

        # 2. Fix Eureka's identity tags
        eureka = db.query(Character).filter(Character.name == "Eureka").first()
        if eureka:
            print("Fixing Eureka's identity tags (Purple -> Teal/Short hair)...")

            # Find the purple_hair tag link and remove it
            purple_hair_tag = db.query(Tag).filter(Tag.name == "purple_hair").first()
            if purple_hair_tag:
                char_tag = (
                    db.query(CharacterTag)
                    .filter(CharacterTag.character_id == eureka.id, CharacterTag.tag_id == purple_hair_tag.id)
                    .first()
                )
                if char_tag:
                    db.delete(char_tag)
                    print("  Removed purple_hair tag")

            # Add short_hair and teal_hair (or light_blue_hair)
            new_tag_names = ["short_hair", "teal_hair"]
            for name in new_tag_names:
                tag = db.query(Tag).filter(Tag.name == name).first()
                if not tag:
                    tag = Tag(name=name, category="character", group_name="hair_color", default_layer=2)
                    db.add(tag)
                    db.flush()

                # Check if link exists
                exists = (
                    db.query(CharacterTag)
                    .filter(CharacterTag.character_id == eureka.id, CharacterTag.tag_id == tag.id)
                    .first()
                )
                if not exists:
                    db.add(CharacterTag(character_id=eureka.id, tag_id=tag.id, is_permanent=True))
                    print(f"  Added {name} tag")

            # Update Eureka's reference prompt too
            eureka.reference_base_prompt = "masterpiece, best_quality, ultra-detailed, solo, upper_body, portrait, facing_viewer, front_view, looking_at_viewer, straight_on, white_background, simple_background, plain_background, solid_background, eureka (eureka seven), short_hair, teal_hair"
            print("  Updated Eureka reference prompt")

        db.commit()
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
