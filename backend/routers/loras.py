"""LoRA CRUD endpoints with Civitai integration."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from models import LoRA
from schemas import LoRACreate, LoRAResponse, LoRAUpdate

router = APIRouter(prefix="/loras", tags=["loras"])


@router.get("", response_model=list[LoRAResponse])
async def list_loras(db: Session = Depends(get_db)):
    """List all LoRAs."""
    loras = db.query(LoRA).order_by(LoRA.name).all()
    logger.info("📋 [LoRAs] Listed %d loras", len(loras))
    return loras


@router.get("/search-civitai")
async def search_civitai(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50),
):
    """Search LoRAs on Civitai. Returns metadata for import."""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://civitai.com/api/v1/models",
                params={"query": query, "types": "LORA", "limit": limit, "sort": "Most Downloaded"},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for model in data.get("items", []):
            # Get first version for details
            versions = model.get("modelVersions", [])
            version = versions[0] if versions else {}

            results.append({
                "civitai_id": model.get("id"),
                "name": model.get("name"),
                "creator": model.get("creator", {}).get("username"),
                "downloads": model.get("stats", {}).get("downloadCount", 0),
                "rating": model.get("stats", {}).get("rating", 0),
                "tags": model.get("tags", []),
                "trigger_words": version.get("trainedWords", []),
                "base_model": version.get("baseModel"),
                "preview_image": version.get("images", [{}])[0].get("url") if version.get("images") else None,
                "civitai_url": f"https://civitai.com/models/{model.get('id')}",
            })

        logger.info("🔍 [Civitai] Searched '%s': %d results", query, len(results))
        return {"query": query, "results": results}

    except httpx.HTTPError as e:
        logger.error("Civitai search failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Civitai API error: {e}")


@router.post("/import-civitai/{civitai_id}", response_model=LoRAResponse)
async def import_from_civitai(civitai_id: int, db: Session = Depends(get_db)):
    """Import LoRA metadata from Civitai by model ID."""
    import httpx

    # Check if already imported
    existing = db.query(LoRA).filter(LoRA.civitai_id == civitai_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"LoRA already imported: {existing.name}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://civitai.com/api/v1/models/{civitai_id}",
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

        # Get first version
        versions = data.get("modelVersions", [])
        if not versions:
            raise HTTPException(status_code=404, detail="No versions found")
        version = versions[0]

        # Extract LoRA info
        lora = LoRA(
            name=data.get("name", "").replace(" ", "_").lower(),
            display_name=data.get("name"),
            civitai_id=civitai_id,
            civitai_url=f"https://civitai.com/models/{civitai_id}",
            trigger_words=version.get("trainedWords", []),
            default_weight=0.7,  # Optimal for scene expression
            weight_min=0.5,
            weight_max=1.5,
            base_models=[version.get("baseModel")] if version.get("baseModel") else None,
            preview_image_url=version.get("images", [{}])[0].get("url") if version.get("images") else None,
        )

        db.add(lora)
        db.commit()
        db.refresh(lora)
        logger.info("✅ [Civitai] Imported LoRA: %s (ID: %d)", lora.name, civitai_id)
        return lora

    except httpx.HTTPError as e:
        logger.error("Civitai import failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Civitai API error: {e}")


@router.get("/{lora_id}", response_model=LoRAResponse)
async def get_lora(lora_id: int, db: Session = Depends(get_db)):
    """Get a single LoRA by ID."""
    lora = db.query(LoRA).filter(LoRA.id == lora_id).first()
    if not lora:
        raise HTTPException(status_code=404, detail="LoRA not found")
    return lora


@router.post("", response_model=LoRAResponse, status_code=201)
async def create_lora(data: LoRACreate, db: Session = Depends(get_db)):
    """Create a new LoRA."""
    existing = db.query(LoRA).filter(LoRA.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="LoRA already exists")

    lora = LoRA(**data.model_dump())
    db.add(lora)
    db.commit()
    db.refresh(lora)
    logger.info("✅ [LoRAs] Created: %s", lora.name)
    return lora


@router.put("/{lora_id}", response_model=LoRAResponse)
async def update_lora(lora_id: int, data: LoRAUpdate, db: Session = Depends(get_db)):
    """Update an existing LoRA."""
    lora = db.query(LoRA).filter(LoRA.id == lora_id).first()
    if not lora:
        raise HTTPException(status_code=404, detail="LoRA not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lora, key, value)

    db.commit()
    db.refresh(lora)
    logger.info("✏️ [LoRAs] Updated: %s", lora.name)
    return lora


@router.delete("/{lora_id}")
async def delete_lora(lora_id: int, db: Session = Depends(get_db)):
    """Delete a LoRA."""
    lora = db.query(LoRA).filter(LoRA.id == lora_id).first()
    if not lora:
        raise HTTPException(status_code=404, detail="LoRA not found")

    name = lora.name
    db.delete(lora)
    db.commit()
    logger.info("🗑️ [LoRAs] Deleted: %s", name)
    return {"ok": True, "deleted": name}
