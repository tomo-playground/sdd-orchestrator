import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import logger
from database import SessionLocal
from models import Character, LoRA


def main():
    db = SessionLocal()
    try:
        # Get available LoRAs
        eureka_lora = db.query(LoRA).filter(LoRA.name == "eureka_v9").first()
        midoriya_lora = db.query(LoRA).filter(LoRA.name == "mha_midoriya-10").first()

        characters_data = [
            {
                "name": "Eureka",
                "description": "Eureka anime character from Eureka Seven",
                "gender": "female",
                "loras": [{"lora_id": eureka_lora.id, "weight": 0.8}] if eureka_lora else None,
                "recommended_negative": ["worst quality, low quality, lowres, bad anatomy", "worst quality, low quality, lowres"],
                "custom_base_prompt": "1girl, eureka, purple hair, green eyes",
                "reference_base_prompt": "masterpiece, best quality, anime portrait, eureka, purple hair, green eyes, clean background, looking at viewer",
                "reference_negative_prompt": "worst quality, low quality, lowres, bad anatomy, blurry",
                "ip_adapter_weight": 0.80,
                "ip_adapter_model": "clip_face",
            },
            {
                "name": "Midoriya",
                "description": "Midoriya Izuku from My Hero Academia",
                "gender": "male",
                "loras": [{"lora_id": midoriya_lora.id, "weight": 0.8}] if midoriya_lora else None,
                "recommended_negative": ["worst quality, low quality, lowres, bad anatomy", "worst quality, low quality, lowres"],
                "custom_base_prompt": "1boy, midoriya izuku, green hair, green eyes",
                "reference_base_prompt": "masterpiece, best quality, anime portrait, midoriya izuku, green hair, green eyes, clean background, looking at viewer",
                "reference_negative_prompt": "worst quality, low quality, lowres, bad anatomy, blurry",
                "ip_adapter_weight": 0.80,
                "ip_adapter_model": "clip_face",
            },
            {
                "name": "Generic Anime Girl",
                "description": "Standard anime female character",
                "gender": "female",
                "loras": None,
                "recommended_negative": ["worst quality, low quality, lowres, bad anatomy", "worst quality, low quality, lowres"],
                "custom_base_prompt": "1girl, anime style",
                "reference_base_prompt": "masterpiece, best quality, anime portrait, 1girl, clean background, looking at viewer",
                "reference_negative_prompt": "worst quality, low quality, lowres, bad anatomy, blurry",
                "ip_adapter_weight": 0.75,
                "ip_adapter_model": "clip_face",
            },
            {
                "name": "Generic Anime Boy",
                "description": "Standard anime male character",
                "gender": "male",
                "loras": None,
                "recommended_negative": ["worst quality, low quality, lowres, bad anatomy", "worst quality, low quality, lowres"],
                "custom_base_prompt": "1boy, anime style",
                "reference_base_prompt": "masterpiece, best quality, anime portrait, 1boy, clean background, looking at viewer",
                "reference_negative_prompt": "worst quality, low quality, lowres, bad anatomy, blurry",
                "ip_adapter_weight": 0.75,
                "ip_adapter_model": "clip_face",
            },
        ]

        created_count = 0
        for char_data in characters_data:
            # Check if character already exists
            existing = db.query(Character).filter(Character.name == char_data["name"]).first()
            if existing:
                logger.info(f"⏭️  Skipping existing character: {char_data['name']}")
                continue

            character = Character(**char_data)
            db.add(character)
            created_count += 1
            logger.info(f"✅ Created character: {char_data['name']}")

        db.commit()
        logger.info(f"🎉 Character creation complete! Created {created_count} new characters.")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error creating characters: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
