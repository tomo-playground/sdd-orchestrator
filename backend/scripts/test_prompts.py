"""Test V3 character-based prompt generation."""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import logger
from database import SessionLocal
from services.prompt.service import PromptService


async def test_character_prompt():
    """Test generating prompts with prompt engine for different characters."""
    db = SessionLocal()
    try:
        service = PromptService(db)

        # Test scene tags
        scene_tags = ["smile", "standing", "classroom", "cowboy_shot"]

        # Test with different characters
        test_cases = [
            {"character_id": 2, "name": "Eureka"},
            {"character_id": 3, "name": "Midoriya"},
            {"character_id": 4, "name": "Generic Anime Girl"},
        ]

        for test in test_cases:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing character: {test['name']} (ID: {test['character_id']})")
            logger.info(f"{'='*60}")

            try:
                prompt = service.generate_prompt_for_scene(
                    character_id=test['character_id'],
                    scene_tags=scene_tags
                )

                logger.info("✅ Generated prompt:")
                logger.info(f"{prompt}")
                logger.info("")

            except Exception as e:
                logger.error(f"❌ Failed for {test['name']}: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_character_prompt())
