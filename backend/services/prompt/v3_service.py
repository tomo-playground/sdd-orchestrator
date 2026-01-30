"""Service layer for V3 Prompt Engine integration."""


from sqlalchemy.orm import Session

from database import SessionLocal
from services.prompt.v3_composition import V3PromptBuilder


class V3PromptService:
    """Unified service for generating V3 prompts for characters and scenes."""

    def __init__(self, db: Session):
        self.builder = V3PromptBuilder(db)

    def generate_prompt_for_scene(
        self,
        character_id: int | None,
        scene_tags: list[str],
        style_loras: list[dict] | None = None,
    ) -> str:
        """Generates a full V3 prompt for a specific scene and character."""
        if character_id:
            return self.builder.compose_for_character(
                character_id=character_id,
                scene_tags=scene_tags,
                style_loras=style_loras
            )
        else:
            return self.builder.compose(
                tags=scene_tags,
                style_loras=style_loras
            )

def get_v3_prompt_service():
    db = SessionLocal()
    try:
        yield V3PromptService(db)
    finally:
        db.close()
