"""Character CRUD endpoints — thin HTTP layer.

Business logic lives in services.characters package.
Router only handles HTTP mapping + error conversion.
"""

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from schemas import (
    AssignPreviewRequest,
    AssignPreviewResponse,
    BatchRegenerateResponse,
    CharacterCreate,
    CharacterDuplicateRequest,
    CharacterDuplicateResponse,
    CharacterEditPreviewResponse,
    CharacterEnhancePreviewResponse,
    CharacterPreviewRequest,
    CharacterPreviewResponse,
    CharacterResponse,
    CharacterUpdate,
    OkDeletedResponse,
    OkRestoredResponse,
    PaginatedCharacterList,
    RegenerateReferenceRequest,
    RegenerateReferenceResponse,
    TrashedItem,
)
from services.characters import (
    ConflictError,
    assign_wizard_preview,
    batch_regenerate_references,
    create_character,
    duplicate_character,
    edit_preview,
    enhance_preview,
    generate_wizard_preview,
    get_character_or_raise,
    list_characters,
    list_trashed_characters,
    permanently_delete_character,
    regenerate_reference,
    restore_character,
    soft_delete_character,
    update_character,
)

service_router = APIRouter(prefix="/characters", tags=["characters"])
admin_router = APIRouter(prefix="/characters", tags=["characters-admin"])


@service_router.get("/trash", response_model=list[TrashedItem])
async def list_trashed_characters_endpoint(db: Session = Depends(get_db)):
    """List soft-deleted characters."""
    return list_trashed_characters(db)


@service_router.get("", response_model=PaginatedCharacterList)
async def list_characters_endpoint(
    group_id: int | None = None,
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List all characters with their tags and tag metadata."""
    return list_characters(db, group_id=group_id, offset=offset, limit=limit)


@service_router.get("/{character_id}", response_model=CharacterResponse)
async def get_character_endpoint(character_id: int, db: Session = Depends(get_db)):
    """Get a single character by ID with tag metadata."""
    try:
        return get_character_or_raise(db, character_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Character not found") from None


@service_router.post("/preview", response_model=CharacterPreviewResponse)
async def preview_character_endpoint(
    data: CharacterPreviewRequest,
    db: Session = Depends(get_db),
):
    """Generate a temporary preview image for the wizard (no DB save)."""
    try:
        return await generate_wizard_preview(db, data)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid preview generation parameters") from None
    except RuntimeError as e:
        from services.error_responses import raise_user_error

        raise_user_error("character_preview", e)


@service_router.post("", response_model=CharacterResponse, status_code=201)
async def create_character_endpoint(data: CharacterCreate, db: Session = Depends(get_db)):
    """Create a new character and link tags."""
    try:
        return create_character(db, data)
    except ConflictError:
        raise HTTPException(status_code=409, detail="Character with this name already exists") from None


@service_router.put("/{character_id}", response_model=CharacterResponse)
async def update_character_endpoint(
    character_id: int,
    data: CharacterUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing character and sync tags."""
    try:
        return update_character(db, character_id, data)
    except ValueError:
        raise HTTPException(status_code=404, detail="Character not found") from None


@service_router.delete("/{character_id}", response_model=OkDeletedResponse)
async def delete_character_endpoint(character_id: int, db: Session = Depends(get_db)):
    """Soft-delete a character."""
    try:
        name = soft_delete_character(db, character_id)
        return {"ok": True, "deleted": name}
    except ValueError:
        raise HTTPException(status_code=404, detail="Character not found") from None


@service_router.post("/{character_id}/restore", response_model=OkRestoredResponse)
async def restore_character_endpoint(character_id: int, db: Session = Depends(get_db)):
    """Restore a soft-deleted character."""
    try:
        name = restore_character(db, character_id)
        return {"ok": True, "restored": name}
    except ValueError:
        raise HTTPException(status_code=404, detail="Character not found") from None


@service_router.post("/{character_id}/duplicate", response_model=CharacterDuplicateResponse, status_code=201)
async def duplicate_character_endpoint(
    character_id: int,
    data: CharacterDuplicateRequest,
    db: Session = Depends(get_db),
):
    """Duplicate a character into a different group."""
    try:
        char = duplicate_character(
            db,
            source_id=character_id,
            target_group_id=data.target_group_id,
            new_name=data.new_name,
            copy_loras=data.should_copy_loras,
            copy_reference=data.should_copy_reference,
        )
        return char
    except ConflictError:
        raise HTTPException(status_code=409, detail="Character with this name already exists") from None
    except ValueError:
        raise HTTPException(status_code=404, detail="Character not found") from None


@admin_router.delete("/{character_id}/permanent", response_model=OkDeletedResponse)
async def permanently_delete_endpoint(character_id: int, db: Session = Depends(get_db)):
    """Permanently delete a character and cleanup IP-Adapter references."""
    try:
        name = permanently_delete_character(db, character_id)
        return {"ok": True, "deleted": name}
    except ValueError:
        raise HTTPException(status_code=404, detail="Character not found") from None


@service_router.post("/{character_id}/regenerate-reference", response_model=RegenerateReferenceResponse)
async def regenerate_reference_endpoint(
    character_id: int,
    data: RegenerateReferenceRequest | None = None,
    db: Session = Depends(get_db),
):
    """Regenerate the character's reference image using its tags and reference prompts."""
    try:
        return await regenerate_reference(
            db,
            character_id,
            controlnet_pose=data.controlnet_pose if data else None,
            num_candidates=data.num_candidates if data else 1,
        )
    except ValueError as e:
        logger.error("[Regenerate] ValueError: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid reference regeneration parameters") from None
    except RuntimeError as e:
        from services.error_responses import raise_user_error

        raise_user_error("character_update", e)


@service_router.post("/{character_id}/generate-voice-ref")
async def generate_voice_ref_endpoint(character_id: int, db: Session = Depends(get_db)):
    """Generate a voice reference sample using Qwen3-TTS."""
    from services.characters.voice_ref import generate_voice_reference  # noqa: PLC0415

    try:
        result = await generate_voice_reference(db, character_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@service_router.post("/{character_id}/enhance-preview", response_model=CharacterEnhancePreviewResponse)
async def enhance_preview_endpoint(character_id: int, db: Session = Depends(get_db)):
    """Enhance the character's preview image using Gemini image generation."""
    try:
        return await enhance_preview(db, character_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Preview enhancement failed") from None


@service_router.post("/{character_id}/edit-preview", response_model=CharacterEditPreviewResponse)
async def edit_preview_endpoint(
    character_id: int,
    instruction: str = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    """Edit the character's preview image with a natural language instruction via Gemini."""
    try:
        return await edit_preview(db, character_id, instruction)
    except ValueError:
        raise HTTPException(status_code=400, detail="Preview edit failed") from None


@service_router.post("/{character_id}/assign-preview", response_model=AssignPreviewResponse)
async def assign_preview_endpoint(
    character_id: int,
    data: AssignPreviewRequest,
    db: Session = Depends(get_db),
):
    """Assign a wizard-generated preview image to an existing character."""
    try:
        return await assign_wizard_preview(db, character_id, data)
    except ValueError:
        raise HTTPException(status_code=400, detail="Preview assignment failed") from None


@admin_router.post("/batch-regenerate-references", response_model=BatchRegenerateResponse)
async def batch_regenerate_references_endpoint(db: Session = Depends(get_db)):
    """Regenerate reference images for ALL characters."""
    return await batch_regenerate_references(db)
