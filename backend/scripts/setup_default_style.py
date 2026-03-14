#!/usr/bin/env python3
"""Setup default SD models, LoRAs, embeddings, and style profile.

Based on current environment:
- Model: noobaiXLNAIXL_vPred10Version (SDXL anime, V-Pred)
- LoRA: eureka_v9 (character), chibi-laugh (style)

Usage:
    cd backend && uv run python scripts/setup_default_style.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from database import SessionLocal
from models import Embedding, LoRA, SDModel, StyleProfile


def get_or_create(db: Session, model_class, name: str, defaults: dict):
    """Get existing or create new record."""
    instance = db.query(model_class).filter(model_class.name == name).first()
    if instance:
        print(f"  ⏭️  Exists: {name}")
        return instance, False

    instance = model_class(name=name, **defaults)
    db.add(instance)
    db.flush()
    print(f"  ✅ Created: {name}")
    return instance, True


def main():
    """Main setup function."""
    print("🚀 Setting up default style configuration...\n")

    db = SessionLocal()
    try:
        # 1. SD Model
        print("📦 SD Models:")
        noobai, _ = get_or_create(
            db,
            SDModel,
            "noobaiXLNAIXL_vPred10Version.safetensors",
            {
                "display_name": "NoobAI-XL V-Pred",
                "model_type": "checkpoint",
                "base_model": "SDXL",
                "description": "SDXL anime model with V-Prediction, high quality and LoRA compatibility",
            },
        )

        # 2. LoRAs
        print("\n🎨 LoRAs:")
        eureka, _ = get_or_create(
            db,
            LoRA,
            "eureka_v9",
            {
                "display_name": "Eureka V9",
                "trigger_words": ["eureka"],
                "default_weight": 1.0,
                "weight_min": 0.5,
                "weight_max": 1.5,
                "base_models": ["SDXL", "noobai-xl"],
                "character_defaults": {
                    "hair_color": "aqua_hair",
                    "eye_color": "purple_eyes",
                    "hair_style": "short_hair",
                },
                "recommended_negative": ["worst quality, low quality, lowres, bad anatomy"],
            },
        )

        chibi, _ = get_or_create(
            db,
            LoRA,
            "chibi-laugh",
            {
                "display_name": "Chibi Laugh",
                "trigger_words": ["chibi", "eyebrow", "laughing", "eyebrow_down"],
                "default_weight": 0.6,
                "weight_min": 0.3,
                "weight_max": 0.8,
                "base_models": ["*"],
                "recommended_negative": ["worst quality, low quality, lowres"],
            },
        )

        # 3. Embeddings (SDXL uses text-based negatives, no SD1.5 embeddings needed)
        print("\n🔖 Embeddings: (skipped — SDXL uses text-based negatives)")

        # 4. Style Profile
        print("\n🎭 Style Profiles:")
        existing_profile = db.query(StyleProfile).filter(StyleProfile.name == "noobai-xl-default").first()
        if existing_profile:
            print("  ⏭️  Exists: noobai-xl-default")
        else:
            profile = StyleProfile(
                name="noobai-xl-default",
                display_name="NoobAI-XL V-Pred Default",
                description="Default style with NoobAI-XL V-Pred, Eureka, and Chibi Laugh LoRAs",
                sd_model_id=noobai.id,
                loras=[
                    {"lora_id": eureka.id, "weight": 1.0},
                    {"lora_id": chibi.id, "weight": 0.6},
                ],
                negative_embeddings=[],
                default_positive="masterpiece, best_quality, highly_detailed",
                default_negative="worst quality, low quality, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, normal quality, jpeg artifacts, signature, watermark, username, blurry",
                is_default=True,
                is_active=True,
            )
            db.add(profile)
            print("  ✅ Created: noobai-xl-default (set as default)")

        db.commit()
        print("\n🎉 Setup complete!")

        # Summary
        print("\n📊 Summary:")
        print(f"  - SD Models: {db.query(SDModel).count()}")
        print(f"  - LoRAs: {db.query(LoRA).count()}")
        print(f"  - Embeddings: {db.query(Embedding).count()}")
        print(f"  - Style Profiles: {db.query(StyleProfile).count()}")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
