"""Character CRUD business logic.

Extracted from routers/characters.py. Raises ValueError (404/400) or
ConflictError (409) — the router converts these to HTTPException.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session, joinedload

from config import (
    DEFAULT_REFERENCE_BASE_PROMPT,
    DEFAULT_REFERENCE_NEGATIVE_PROMPT,
    logger,
)
from models import Character, CharacterTag, LoRA
from schemas import CharacterCreate, CharacterTagLink, CharacterUpdate

from .lora_enrichment import enrich_character_loras, enrich_with_lora_map


class ConflictError(Exception):
    """Raised when a unique constraint would be violated (e.g. duplicate name)."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _base_character_query(db: Session):
    """Shared joinedload pattern for character queries."""
    return db.query(Character).options(
        joinedload(Character.tags).joinedload(CharacterTag.tag),
        joinedload(Character.style_profile),
    )


def _populate_tag_metadata(character: Character) -> None:
    """Copy tag.name / tag.default_layer / tag.group_name onto CharacterTag for serialization."""
    for char_tag in character.tags:
        char_tag.name = char_tag.tag.name
        char_tag.layer = char_tag.tag.default_layer
        char_tag.group_name = char_tag.tag.group_name


def _populate_style_profile_name(character: Character) -> None:
    """Set style_profile_name from the joined relationship for serialization."""
    character.style_profile_name = (
        character.style_profile.name if character.style_profile else None
    )


def _merge_tags(data) -> list:
    """Merge V3 'tags' with legacy 'identity_tags' / 'clothing_tags'."""
    final_tags: list = []
    if data.tags:
        final_tags.extend(data.tags)

    if data.identity_tags:
        for tid in data.identity_tags:
            if not any(t.tag_id == tid for t in final_tags):
                final_tags.append(CharacterTagLink(tag_id=tid, is_permanent=True))

    if data.clothing_tags:
        for tid in data.clothing_tags:
            if not any(t.tag_id == tid for t in final_tags):
                final_tags.append(CharacterTagLink(tag_id=tid, is_permanent=False))

    return final_tags


def _save_tag_links(db: Session, character_id: int, tags: list) -> None:
    """Persist CharacterTag rows from a list of CharacterTagLink objects."""
    for tag_link in tags:
        db.add(
            CharacterTag(
                character_id=character_id,
                tag_id=tag_link.tag_id,
                weight=tag_link.weight,
                is_permanent=tag_link.is_permanent,
            )
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_characters(
    db: Session,
    project_id: int | None = None,
    style_profile_id: int | None = None,
    offset: int = 0,
    limit: int = 50,
) -> dict:
    """List characters with tags and enriched LoRA metadata (paginated)."""
    from sqlalchemy import func

    base = db.query(Character).filter(Character.deleted_at.is_(None))
    if project_id is not None:
        base = base.filter(Character.project_id == project_id)
    if style_profile_id is not None:
        base = base.filter(Character.style_profile_id == style_profile_id)

    total = base.with_entities(func.count(Character.id)).scalar() or 0

    characters = (
        base.options(
            joinedload(Character.tags).joinedload(CharacterTag.tag),
            joinedload(Character.style_profile),
        )
        .order_by(Character.name)
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Pre-fetch all LoRAs to avoid N+1
    all_loras = db.query(LoRA).all()
    lora_map = {lora.id: lora for lora in all_loras}

    for char in characters:
        _populate_tag_metadata(char)
        _populate_style_profile_name(char)
        if char.loras:
            char.loras = enrich_with_lora_map(char.loras, lora_map)

    return {"items": characters, "total": total, "offset": offset, "limit": limit}


def get_character_or_raise(db: Session, character_id: int) -> Character:
    """Fetch a single character with tags, raise ValueError if not found."""
    character = _base_character_query(db).filter(Character.id == character_id, Character.deleted_at.is_(None)).first()
    if not character:
        raise ValueError("Character not found")

    _populate_tag_metadata(character)
    _populate_style_profile_name(character)
    if character.loras:
        character.loras = enrich_character_loras(db, character.loras)

    return character


def create_character(db: Session, data: CharacterCreate) -> Character:
    """Create a character with tags, LoRA enrichment, and default prompts."""
    existing = db.query(Character).filter(Character.name == data.name, Character.deleted_at.is_(None)).first()
    if existing:
        raise ConflictError("Character name already exists")

    char_data = data.model_dump(exclude={"tags", "identity_tags", "clothing_tags"})

    if char_data.get("loras"):
        char_data["loras"] = enrich_character_loras(db, char_data["loras"])

    if not char_data.get("reference_base_prompt"):
        char_data["reference_base_prompt"] = DEFAULT_REFERENCE_BASE_PROMPT
    if not char_data.get("reference_negative_prompt"):
        char_data["reference_negative_prompt"] = DEFAULT_REFERENCE_NEGATIVE_PROMPT

    character = Character(**char_data)
    db.add(character)
    db.flush()

    final_tags = _merge_tags(data)
    if final_tags:
        _save_tag_links(db, character.id, final_tags)

    db.commit()
    return get_character_or_raise(db, character.id)


def update_character(db: Session, character_id: int, data: CharacterUpdate) -> Character:
    """Update an existing character and sync tags."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise ValueError("Character not found")

    update_data = data.model_dump(
        exclude={"tags", "identity_tags", "clothing_tags"},
        exclude_unset=True,
    )

    if "loras" in update_data and update_data["loras"]:
        update_data["loras"] = enrich_character_loras(db, update_data["loras"])

    for key, value in update_data.items():
        setattr(character, key, value)

    if data.tags is not None or data.identity_tags is not None or data.clothing_tags is not None:
        db.query(CharacterTag).filter(CharacterTag.character_id == character_id).delete()
        final_tags = _merge_tags(data)
        _save_tag_links(db, character_id, final_tags)

    db.commit()
    return get_character_or_raise(db, character_id)


def soft_delete_character(db: Session, character_id: int) -> str:
    """Soft-delete a character. Returns character name."""
    character = db.query(Character).filter(Character.id == character_id, Character.deleted_at.is_(None)).first()
    if not character:
        raise ValueError("Character not found")

    character.deleted_at = datetime.now(UTC)
    db.commit()
    logger.info("[Characters] Soft deleted: %s", character.name)
    return character.name


def restore_character(db: Session, character_id: int) -> str:
    """Restore a soft-deleted character. Returns character name."""
    character = db.query(Character).filter(Character.id == character_id, Character.deleted_at.isnot(None)).first()
    if not character:
        raise ValueError("Trashed character not found")

    character.deleted_at = None
    db.commit()
    logger.info("[Characters] Restored: %s", character.name)
    return character.name


def permanently_delete_character(db: Session, character_id: int) -> str:
    """Permanently delete a character and cleanup reference images via AssetService."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise ValueError("Character not found")

    name = character.name
    try:
        from services.controlnet import delete_reference_image

        delete_reference_image(name)
    except Exception as e:
        logger.warning("[Characters] Failed to delete reference image for %s: %s", name, e)

    db.delete(character)
    db.commit()
    logger.info("[Characters] Permanently deleted: %s", name)
    return name


def list_trashed_characters(db: Session) -> list[dict]:
    """List soft-deleted characters (id, name, deleted_at)."""
    items = db.query(Character).filter(Character.deleted_at.isnot(None)).order_by(Character.deleted_at.desc()).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "deleted_at": c.deleted_at.isoformat() if c.deleted_at else None,
        }
        for c in items
    ]
