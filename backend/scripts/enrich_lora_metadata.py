import asyncio
import sys
from pathlib import Path

import httpx

# Add backend directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import logger
from database import SessionLocal
from models import LoRA


async def search_civitai_for_lora(client, lora_name):
    """Search Civitai for a LoRA by name."""
    try:
        # Clean name for search (remove underscores, etc)
        search_query = lora_name.replace("_", " ")

        response = await client.get(
            "https://civitai.com/api/v1/models",
            params={"query": search_query, "types": "LORA", "limit": 1, "sort": "Most Downloaded"},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])
        if items:
            return items[0]  # Return best match
        return None
    except Exception as e:
        logger.warning(f"⚠️ Search failed for '{lora_name}': {e}")
        return None


async def update_lora_metadata(client, db, lora):
    """Update a single LoRA with data from Civitai."""
    logger.info(f"🔎 Searching Civitai for: {lora.name}")

    metadata = await search_civitai_for_lora(client, lora.name)

    if not metadata:
        logger.info(f"   ❌ No match found for '{lora.name}'")
        return False

    # Extract version info (first one)
    civitai_id = metadata.get("id")
    versions = metadata.get("modelVersions", [])
    if not versions:
        return False

    version = versions[0]

    # Update fields if they are missing or can be enriched
    updated = False

    if not lora.civitai_id:
        lora.civitai_id = civitai_id
        updated = True

    if not lora.civitai_url:
        lora.civitai_url = f"https://civitai.com/models/{civitai_id}"
        updated = True

    if not lora.trigger_words:
        triggers = version.get("trainedWords", [])
        if triggers:
            lora.trigger_words = triggers
            # Also try to clean up display name if it's just the filename
            updated = True
            logger.info(f"   ✨ Found triggers: {triggers}")

    if not lora.preview_image_url:
        images = version.get("images", [])
        if images:
            lora.preview_image_url = images[0].get("url")
            updated = True

    # Infer LoRA Type from tags
    tags = metadata.get("tags", [])
    inferred_type = "style"  # Default

    # Priority based inference
    lower_tags = [t.lower() for t in tags]

    if any(t in lower_tags for t in ["character", "person", "celebrity", "anime character"]):
        inferred_type = "character"
    elif any(t in lower_tags for t in ["pose", "posing"]):
        inferred_type = "pose"
    elif any(t in lower_tags for t in ["clothing", "outfit", "costume"]):
        inferred_type = "concept"
    elif any(t in lower_tags for t in ["style", "art style", "aesthetic"]):
        inferred_type = "style"
    else:
        # Fallback heuristics based on name
        name_lower = lora.name.lower()
        if any(x in name_lower for x in ["style", "art", "mix"]):
            inferred_type = "style"
        elif any(x in name_lower for x in ["pose"]):
            inferred_type = "pose"

    # Update type if it's currently generic "style" or we have a better guess
    # (Assuming we want to overwrite 'style' with 'character' if found)
    if lora.lora_type == "style" and inferred_type != "style":
        lora.lora_type = inferred_type
        updated = True
        logger.info(f"   🧠 Inferred type: {inferred_type} (was {lora.lora_type})")
    elif not lora.lora_type:
        lora.lora_type = inferred_type
        updated = True
        logger.info(f"   🧠 Inferred type: {inferred_type}")

    if updated:
        db.commit()
        db.refresh(lora)
        logger.info(f"   ✅ Updated metadata for: {lora.name}")
        return True
    else:
        logger.info(f"   Unknown changes or already up to date for: {lora.name}")
        return False


async def main():
    logger.info("🚀 Starting Civitai Metadata Enrichment...")

    db = SessionLocal()
    try:
        # Get all LoRAs
        loras = db.query(LoRA).all()
        logger.info(f"📚 Found {len(loras)} LoRAs in database.")

        async with httpx.AsyncClient(timeout=15.0) as client:
            updated_count = 0
            for lora in loras:
                # Skip if already fully populated
                if lora.civitai_id and lora.trigger_words and lora.lora_type and lora.lora_type != "style":
                    continue

                if await update_lora_metadata(client, db, lora):
                    updated_count += 1

                # Rate limiting to be nice
                await asyncio.sleep(1)

        logger.info(f"🎉 Enrichment complete! Updated {updated_count} LoRAs.")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
