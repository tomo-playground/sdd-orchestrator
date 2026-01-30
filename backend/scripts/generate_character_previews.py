"""Generate preview images for all characters using their reference prompts."""
import asyncio
import sys
from pathlib import Path

import httpx

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import SD_BASE_URL, logger
from database import SessionLocal
from models import Character


async def generate_character_preview(client, character):
    """Generate a preview image for a character."""
    logger.info(f"🎨 Generating preview for: {character.name}")

    # Use reference prompt or custom prompt
    prompt = character.reference_base_prompt or character.custom_base_prompt or "1girl, anime style"
    negative = character.reference_negative_prompt or character.custom_negative_prompt or "verybadimagenegative_v1.3"

    # Add LoRA if available
    if character.loras and len(character.loras) > 0:
        lora_id = character.loras[0]["lora_id"]
        weight = character.loras[0]["weight"]
        # We need to fetch LoRA name from DB
        from models import LoRA
        db = SessionLocal()
        lora = db.query(LoRA).filter(LoRA.id == lora_id).first()
        db.close()

        if lora:
            # Add trigger words
            if lora.trigger_words:
                prompt = f"{', '.join(lora.trigger_words[:3])}, {prompt}"
            # Add LoRA tag
            prompt = f"{prompt}, <lora:{lora.name}:{weight}>"

    logger.info(f"   Prompt: {prompt[:100]}...")

    # Generate image via SD WebUI
    payload = {
        "prompt": prompt,
        "negative_prompt": negative,
        "steps": 20,
        "cfg_scale": 7.0,
        "width": 512,
        "height": 768,
        "sampler_name": "DPM++ 2M Karras",
        "seed": -1,
    }

    try:
        response = await client.post(
            f"{SD_BASE_URL}/sdapi/v1/txt2img",
            json=payload,
            timeout=120.0
        )
        response.raise_for_status()
        result = response.json()

        if result.get("images"):
            # Save image
            import base64
            from pathlib import Path

            image_data = base64.b64decode(result["images"][0])
            filename = f"character_preview_{character.name.lower().replace(' ', '_')}.png"
            filepath = Path("outputs/images/stored") / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, "wb") as f:
                f.write(image_data)

            preview_url = f"/outputs/images/stored/{filename}"
            logger.info(f"   ✅ Saved: {preview_url}")
            return preview_url
        else:
            logger.error("   ❌ No image generated")
            return None

    except Exception as e:
        logger.error(f"   ❌ Generation failed: {e}")
        return None

async def main():
    db = SessionLocal()
    try:
        # Get characters without preview images
        characters = db.query(Character).filter(
            (Character.preview_image_url == None) | (Character.preview_image_url == "")
        ).all()

        if not characters:
            logger.info("✅ All characters already have preview images")
            return

        logger.info(f"📸 Generating previews for {len(characters)} characters...")

        async with httpx.AsyncClient() as client:
            for char in characters:
                preview_url = await generate_character_preview(client, char)
                if preview_url:
                    char.preview_image_url = preview_url
                    db.commit()
                    logger.info(f"✅ Updated {char.name} with preview URL")

                # Rate limiting
                await asyncio.sleep(2)

        logger.info("🎉 Preview generation complete!")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
