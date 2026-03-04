"""Service layer for Prompt Engine integration."""

from sqlalchemy.orm import Session

from database import SessionLocal
from services.prompt.composition import PromptBuilder


class PromptService:
    """Unified service for generating prompts for characters and scenes."""

    def __init__(self, db: Session):
        self.builder = PromptBuilder(db)

    def generate_prompt_for_scene(
        self,
        character_id: int,
        scene_tags: list[str],
        style_loras: list[dict] | None = None,
    ) -> str:
        """Generates a full prompt for a specific scene and character."""
        return self.builder.compose_for_character(
            character_id=character_id, scene_tags=scene_tags, style_loras=style_loras
        )


def get_prompt_service():
    db = SessionLocal()
    try:
        yield PromptService(db)
    finally:
        db.close()
