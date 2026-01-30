"""Create default style profiles."""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import logger
from database import SessionLocal
from models import Embedding, SDModel, StyleProfile


def main():
    db = SessionLocal()
    try:
        # Get first SD model
        sd_model = db.query(SDModel).first()
        if not sd_model:
            logger.error("❌ No SD models found. Run sync_webui_data.py first.")
            return

        # Get negative embeddings
        negative_embs = db.query(Embedding).filter(
            Embedding.embedding_type == "negative"
        ).all()
        negative_emb_ids = [emb.id for emb in negative_embs]

        # Create default profile
        default_profile = db.query(StyleProfile).filter(
            StyleProfile.name == "Default Anime"
        ).first()

        if not default_profile:
            default_profile = StyleProfile(
                name="Default Anime",
                display_name="Default Anime Style",
                description="Standard anime style with quality tags",
                sd_model_id=sd_model.id,
                loras=[],
                negative_embeddings=negative_emb_ids,
                positive_embeddings=[],
                default_positive="masterpiece, best_quality, high_quality, anime coloring",
                default_negative=", ".join([emb.trigger_word for emb in negative_embs]),
                is_default=True,
                is_active=True
            )
            db.add(default_profile)
            db.commit()
            logger.info(f"✅ Created default profile: {default_profile.name}")
        else:
            logger.info(f"⏭️  Default profile already exists: {default_profile.name}")

        # Create realistic profile if realistic model exists
        realistic_model = db.query(SDModel).filter(
            SDModel.name.ilike("%realistic%")
        ).first()

        if realistic_model:
            realistic_profile = db.query(StyleProfile).filter(
                StyleProfile.name == "Realistic"
            ).first()

            if not realistic_profile:
                realistic_profile = StyleProfile(
                    name="Realistic",
                    display_name="Realistic Style",
                    description="Photorealistic image generation",
                    sd_model_id=realistic_model.id,
                    loras=[],
                    negative_embeddings=negative_emb_ids,
                    positive_embeddings=[],
                    default_positive="masterpiece, best_quality, high_quality, photorealistic, detailed",
                    default_negative=", ".join([emb.trigger_word for emb in negative_embs]),
                    is_default=False,
                    is_active=True
                )
                db.add(realistic_profile)
                db.commit()
                logger.info(f"✅ Created realistic profile: {realistic_profile.name}")

        logger.info("🎉 Style profiles created successfully!")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error creating style profiles: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
