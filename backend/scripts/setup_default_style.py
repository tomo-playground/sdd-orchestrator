#!/usr/bin/env python3
"""Setup default SD models, LoRAs, embeddings, and style profile.

Based on current environment:
- Model: anyloraCheckpoint_bakedvaeBlessedFp16.safetensors (SD1.5 anime, style-neutral, best prompt fidelity)
- LoRA: eureka_v9 (character), chibi-laugh (style)
- Negative Embeddings: verybadimagenegative_v1.3, easynegative

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
        anylora, _ = get_or_create(
            db,
            SDModel,
            "anyloraCheckpoint_bakedvaeBlessedFp16.safetensors",
            {
                "display_name": "AnyLoRA",
                "model_type": "checkpoint",
                "base_model": "SD1.5",
                "description": "Style-neutral SD1.5 model, best prompt fidelity and LoRA compatibility",
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
                "base_models": ["SD1.5", "anylora"],
                "character_defaults": {
                    "hair_color": "aqua_hair",
                    "eye_color": "purple_eyes",
                    "hair_style": "short_hair",
                },
                "recommended_negative": ["verybadimagenegative_v1.3"],
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
                "recommended_negative": ["easynegative"],
            },
        )

        # 3. Embeddings
        print("\n🔖 Embeddings:")
        veryBad, _ = get_or_create(
            db,
            Embedding,
            "verybadimagenegative_v1.3",
            {
                "display_name": "Very Bad Image Negative",
                "embedding_type": "negative",
                "trigger_word": "verybadimagenegative_v1.3",
                "description": "Quality improvement negative embedding",
            },
        )

        easyNeg, _ = get_or_create(
            db,
            Embedding,
            "easynegative",
            {
                "display_name": "Easy Negative",
                "embedding_type": "negative",
                "trigger_word": "easynegative",
                "description": "General negative embedding for better quality",
            },
        )

        # 4. Style Profile
        print("\n🎭 Style Profiles:")
        existing_profile = db.query(StyleProfile).filter(StyleProfile.name == "anylora-default").first()
        if existing_profile:
            print("  ⏭️  Exists: anylora-default")
        else:
            profile = StyleProfile(
                name="anylora-default",
                display_name="AnyLoRA Default",
                description="Default style with AnyLoRA, Eureka, and Chibi Laugh LoRAs",
                sd_model_id=anylora.id,
                loras=[
                    {"lora_id": eureka.id, "weight": 1.0},
                    {"lora_id": chibi.id, "weight": 0.6},
                ],
                negative_embeddings=[veryBad.id, easyNeg.id],
                default_positive="masterpiece, best_quality, highly_detailed",
                default_negative="lowres, bad_anatomy, bad_hands, text, error, missing_fingers, extra_digit, fewer_digits, cropped, worst_quality, low_quality, normal_quality, jpeg_artifacts, signature, watermark, username, blurry",
                is_default=True,
                is_active=True,
            )
            db.add(profile)
            print("  ✅ Created: anylora-default (set as default)")

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
