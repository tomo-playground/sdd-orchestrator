import asyncio
import sys
from pathlib import Path

import httpx

# Add backend directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import SD_BASE_URL, logger
from database import SessionLocal
from models import Embedding, LoRA, SDModel


async def fetch_sd_models(client, db):
    logger.info("📡 Fetching SD Models from WebUI...")
    try:
        response = await client.get(f"{SD_BASE_URL}/sdapi/v1/sd-models")
        response.raise_for_status()
        models = response.json()

        count = 0
        for m in models:
            title = m.get("title")
            model_name = m.get("model_name")
            # hash = m.get("hash")

            # Check if exists
            existing = db.query(SDModel).filter(SDModel.name == title).first()
            if not existing:
                # Fallback if name matches model_name but title is different
                existing = db.query(SDModel).filter(SDModel.name == model_name).first()

            if not existing:
                new_model = SDModel(
                    name=title,
                    display_name=model_name,
                    model_type="checkpoint",
                    base_model="SDXL",  # Default assumption
                    is_active=True
                )
                db.add(new_model)
                count += 1
                logger.info(f"   ➕ Added Checkpoint: {title}")
            else:
                # Update?
                pass
        db.commit()
        logger.info(f"✅ Synced {count} new SD Models.")
    except Exception as e:
        logger.error(f"❌ Failed to fetch SD Models: {e}")

async def fetch_loras(client, db):
    logger.info("📡 Fetching LoRAs from WebUI...")
    try:
        response = await client.get(f"{SD_BASE_URL}/sdapi/v1/loras")
        response.raise_for_status()
        loras = response.json()

        count = 0
        for lora in loras:
            name = lora.get("name")
            alias = lora.get("alias")

            # Check if exists
            existing = db.query(LoRA).filter(LoRA.name == name).first()
            if not existing:
                new_lora = LoRA(
                    name=name,
                    display_name=alias,
                    lora_type="style", # Default
                    default_weight=0.7,
                    trigger_words=[] # Can be populated if parsed from metadata
                )
                db.add(new_lora)
                count += 1
                logger.info(f"   ➕ Added LoRA: {name}")
        db.commit()
        logger.info(f"✅ Synced {count} new LoRAs.")
    except Exception as e:
        logger.error(f"❌ Failed to fetch LoRAs: {e}")

async def fetch_embeddings(client, db):
    logger.info("📡 Fetching Embeddings from WebUI...")
    try:
        response = await client.get(f"{SD_BASE_URL}/sdapi/v1/embeddings")
        response.raise_for_status()
        data = response.json()

        loaded = data.get("loaded", {})
        count = 0

        for name, _info in loaded.items():
            # Check if exists
            existing = db.query(Embedding).filter(Embedding.name == name).first()
            if not existing:
                # Heuristic: Negative embeddings often have "negative" or "bad" in name
                emb_type = "negative" if "neg" in name.lower() or "bad" in name.lower() else "positive"

                new_emb = Embedding(
                    name=name,
                    display_name=name,
                    embedding_type=emb_type,
                    trigger_word=name,
                    is_active=True
                )
                db.add(new_emb)
                count += 1
                logger.info(f"   ➕ Added Embedding: {name} ({emb_type})")
        db.commit()
        logger.info(f"✅ Synced {count} new Embeddings.")
    except Exception as e:
        logger.error(f"❌ Failed to fetch Embeddings: {e}")

async def main():
    logger.info(f"🔌 Connecting to SD WebUI at {SD_BASE_URL}...")

    db = SessionLocal()
    async with httpx.AsyncClient(timeout=30.0) as client:
        await fetch_sd_models(client, db)
        await fetch_loras(client, db)
        await fetch_embeddings(client, db)

    db.close()
    logger.info("🎉 Sync complete!")

if __name__ == "__main__":
    asyncio.run(main())
