import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models import Character

# Generic character data
GENERIC_CHARACTERS = [
    {
        "name": "Generic Anime Girl",
        "custom_base_prompt": "1girl, brown_hair, long_hair, brown_eyes, school_uniform, innocent_face",
        "custom_negative_prompt": "nsfw, revealing_clothes, sexy, mature_female, heavy_makeup",
        "reference_base_prompt": "masterpiece, best_quality, (1girl:1.3), (solo:1.3), brown_hair, long_hair, brown_eyes, school_uniform, looking_at_viewer, simple_background, white_background, upper_body, innocent_smile, clean_lineart",
        "reference_negative_prompt": "verybadimagenegative_v1.3, easynegative, (worst_quality, low_quality:1.4), (multiple_girls:1.5), (2girls:1.5), (multiple_people:1.5), nsfw, revealing_clothes, sexy, mature_female, blurry, text, watermark",
    },
    {
        "name": "Generic Anime Boy",
        "custom_base_prompt": "1boy, male_focus, black_hair, short_hair, brown_eyes, masculine, school_uniform",
        "custom_negative_prompt": "nsfw, feminine, breasts, long_eyelashes, lipstick, makeup, muscular, shirtless, mature_male, facial_hair",
        "reference_base_prompt": "masterpiece, best_quality, (1boy:1.3), (solo:1.3), (male_focus:1.2), black_hair, short_hair, brown_eyes, masculine, school_uniform, blazer, looking_at_viewer, simple_background, white_background, upper_body, neutral_expression, clean_lineart",
        "reference_negative_prompt": "verybadimagenegative_v1.3, easynegative, (worst_quality, low_quality:1.4), (multiple_boys:1.5), (2boys:1.5), (multiple_people:1.5), nsfw, feminine, breasts, long_eyelashes, lipstick, makeup, muscular, shirtless, mature_male, blurry, text, watermark",
    },
]

def create_characters():
    db = SessionLocal()
    try:
        created_count = 0
        for char_data in GENERIC_CHARACTERS:
            existing = db.query(Character).filter(Character.name == char_data["name"]).first()
            if existing:
                print(f"  ⏭️  Character exists: {char_data['name']}")
                continue

            new_char = Character(**char_data)
            db.add(new_char)
            created_count += 1
            print(f"  ✅ Created character: {char_data['name']}")

        db.commit()
        print(f"\n🎉 Done! Created {created_count} characters.")
    finally:
        db.close()

if __name__ == "__main__":
    create_characters()
