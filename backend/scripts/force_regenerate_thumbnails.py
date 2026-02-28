import asyncio
import base64
import sys
import uuid
from pathlib import Path

import httpx

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import SD_BASE_URL, logger
from database import SessionLocal
from models import Character, MediaAsset
from services.storage import get_storage

# Force update these IDs
TARGET_IDS = [12, 16, 15, 14, 17, 18, 13]


async def generate_character_preview(client, character, db):
    """Generate a preview image for a character and upload via Storage."""
    logger.info(f"🎨 Generating preview for: {character.name} (ID: {character.id})")

    # Use reference prompt or custom prompt
    prompt = character.reference_base_prompt or character.custom_base_prompt or "1girl, anime style"
    negative = character.reference_negative_prompt or character.custom_negative_prompt or "verybadimagenegative_v1.3"

    # Add LoRA if available
    if character.loras and len(character.loras) > 0:
        lora_id = character.loras[0]["lora_id"]
        weight = character.loras[0]["weight"]
        from models import LoRA

        lora = db.query(LoRA).filter(LoRA.id == lora_id).first()

        if lora:
            if lora.trigger_words:
                prompt = f"{', '.join(lora.trigger_words[:3])}, {prompt}"
            prompt = f"{prompt}, <lora:{lora.name}:{weight}>"

    logger.info(f"   Prompt: {prompt[:100]}...")

    payload = {
        "prompt": prompt,
        "negative_prompt": negative,
        "steps": 30,
        "cfg_scale": 7.0,
        "width": 512,
        "height": 768,
        "sampler_name": "DPM++ 2M Karras",
        "seed": -1,
    }

    try:
        response = await client.post(f"{SD_BASE_URL}/sdapi/v1/txt2img", json=payload, timeout=180.0)
        response.raise_for_status()
        result = response.json()

        if result.get("images"):
            image_data = base64.b64decode(result["images"][0])

            # File name and storage key
            unique_id = uuid.uuid4().hex[:8]
            filename = f"character_{character.id}_preview_{unique_id}.png"
            storage_key = f"characters/{character.id}/preview/{filename}"

            # Save to underlying S3/Local storage wrapper
            storage = get_storage()
            public_url = storage.save(storage_key, image_data, content_type="image/png")

            # Define attributes for MediaAsset explicitly
            asset_kwargs = {
                "file_type": "image",
                "storage_key": storage_key,
                "file_name": filename,
                "mime_type": "image/png",
                "owner_type": "character",
                "owner_id": character.id,
            }

            # Create or update MediaAsset
            if character.preview_image_asset:
                for key, value in asset_kwargs.items():
                    setattr(character.preview_image_asset, key, value)
            else:
                asset = MediaAsset(**asset_kwargs)
                db.add(asset)
                db.flush()
                character.preview_image_asset_id = asset.id

            logger.info(f"   ✅ Saved to Storage: {public_url}")
            return True
        else:
            logger.error("   ❌ No image generated")
            return False

    except Exception as e:
        logger.error(f"   ❌ Generation failed: {e}")
        return False


async def main():
    db = SessionLocal()
    try:
        characters = db.query(Character).filter(Character.id.in_(TARGET_IDS)).all()

        if not characters:
            logger.info("❌ No matching characters found.")
            return

        logger.info(f"📸 Generating previews for {len(characters)} characters...")

        async with httpx.AsyncClient() as client:
            for char in characters:
                success = await generate_character_preview(client, char, db)
                if success:
                    db.commit()
                    logger.info(f"✅ Updated {char.name} with preview MediaAsset")
                else:
                    logger.warning(f"⚠️ Failed to generate image for {char.name}")

                await asyncio.sleep(2)

        logger.info("🎉 Forced preview generation complete!")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
