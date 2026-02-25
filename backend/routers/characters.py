"""Character CRUD endpoints — thin HTTP layer.

Business logic lives in services.characters package.
Router only handles HTTP mapping + error conversion.
"""

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    AssignPreviewRequest,
    AssignPreviewResponse,
    CharacterCreate,
    CharacterPreviewRequest,
    CharacterPreviewResponse,
    CharacterResponse,
    CharacterUpdate,
    PaginatedCharacterList,
    RegenerateReferenceRequest,
    RegenerateReferenceResponse,
)
from services.characters import (
    ConflictError,
    assign_wizard_preview,
    batch_regenerate_references,
    create_character,
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

router = APIRouter(prefix="/characters", tags=["characters"])


@router.get("/trash")
async def list_trashed_characters_endpoint(db: Session = Depends(get_db)):
    """List soft-deleted characters."""
    return list_trashed_characters(db)


@router.get("", response_model=PaginatedCharacterList)
async def list_characters_endpoint(
    style_profile_id: int | None = None,
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List all characters with their tags and tag metadata."""
    return list_characters(db, style_profile_id=style_profile_id, offset=offset, limit=limit)


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character_endpoint(character_id: int, db: Session = Depends(get_db)):
    """Get a single character by ID with tag metadata."""
    try:
        return get_character_or_raise(db, character_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.post("/preview", response_model=CharacterPreviewResponse)
async def preview_character_endpoint(
    data: CharacterPreviewRequest,
    db: Session = Depends(get_db),
):
    """Generate a temporary preview image for the wizard (no DB save)."""
    try:
        return await generate_wizard_preview(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except RuntimeError as e:
        from services.error_responses import raise_user_error

        raise_user_error("character_preview", e)


@router.post("", response_model=CharacterResponse, status_code=201)
async def create_character_endpoint(data: CharacterCreate, db: Session = Depends(get_db)):
    """Create a new character and link tags."""
    try:
        return create_character(db, data)
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character_endpoint(
    character_id: int,
    data: CharacterUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing character and sync tags."""
    try:
        return update_character(db, character_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.delete("/{character_id}")
async def delete_character_endpoint(character_id: int, db: Session = Depends(get_db)):
    """Soft-delete a character."""
    try:
        name = soft_delete_character(db, character_id)
        return {"ok": True, "deleted": name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.post("/{character_id}/restore")
async def restore_character_endpoint(character_id: int, db: Session = Depends(get_db)):
    """Restore a soft-deleted character."""
    try:
        name = restore_character(db, character_id)
        return {"ok": True, "restored": name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.delete("/{character_id}/permanent")
async def permanently_delete_endpoint(character_id: int, db: Session = Depends(get_db)):
    """Permanently delete a character and cleanup IP-Adapter references."""
    try:
        name = permanently_delete_character(db, character_id)
        return {"ok": True, "deleted": name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.post("/{character_id}/regenerate-reference", response_model=RegenerateReferenceResponse)
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
        raise HTTPException(status_code=400, detail=str(e)) from None
    except RuntimeError as e:
        from services.error_responses import raise_user_error

        raise_user_error("character_update", e)


@router.post("/{character_id}/enhance-preview")
async def enhance_preview_endpoint(character_id: int, db: Session = Depends(get_db)):
    """Enhance the character's preview image using Gemini image generation."""
    try:
        return await enhance_preview(db, character_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post("/{character_id}/edit-preview")
async def edit_preview_endpoint(
    character_id: int,
    instruction: str = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    """Edit the character's preview image with a natural language instruction via Gemini."""
    try:
        return await edit_preview(db, character_id, instruction)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post("/{character_id}/assign-preview", response_model=AssignPreviewResponse)
async def assign_preview_endpoint(
    character_id: int,
    data: AssignPreviewRequest,
    db: Session = Depends(get_db),
):
    """Assign a wizard-generated preview image to an existing character."""
    try:
        return await assign_wizard_preview(db, character_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post("/batch-regenerate-references")
async def batch_regenerate_references_endpoint(db: Session = Depends(get_db)):
    """Regenerate reference images for ALL characters."""
    return await batch_regenerate_references(db)
