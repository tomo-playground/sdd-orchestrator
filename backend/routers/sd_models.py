"""SD Model, Embedding CRUD and SD WebUI proxy endpoints."""

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import SD_API_TIMEOUT, SD_LORAS_URL, SD_MODEL_SWITCH_TIMEOUT, SD_MODELS_URL, SD_OPTIONS_URL, logger
from database import get_db
from models import Embedding, SDModel
from schemas import (
    EmbeddingCreate,
    EmbeddingResponse,
    EmbeddingUpdate,
    OkDeletedResponse,
    SDModelCreate,
    SDModelRequest,
    SDModelResponse,
    SDModelUpdate,
    SDWebUILorasResponse,
    SDWebUIModelsResponse,
    SDWebUIOptionsResponse,
    SDWebUIOptionsUpdateResponse,
)

router = APIRouter(tags=["sd-models"])


# ============================================================
# SD Models
# ============================================================


@router.get("/sd-models", response_model=list[SDModelResponse])
async def list_sd_models(active_only: bool = True, db: Session = Depends(get_db)):
    """List all SD models."""
    query = db.query(SDModel)
    if active_only:
        query = query.filter(SDModel.is_active)
    models = query.order_by(SDModel.name).all()
    logger.info("📋 [SDModels] Listed %d models", len(models))
    return models


@router.get("/sd-models/{model_id}", response_model=SDModelResponse)
async def get_sd_model(model_id: int, db: Session = Depends(get_db)):
    """Get a single SD model."""
    model = db.query(SDModel).filter(SDModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="SD model not found")
    return model


@router.post("/sd-models", response_model=SDModelResponse, status_code=201)
async def create_sd_model(data: SDModelCreate, db: Session = Depends(get_db)):
    """Create a new SD model."""
    existing = db.query(SDModel).filter(SDModel.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="SD model already exists")

    model = SDModel(**data.model_dump())
    db.add(model)
    db.commit()
    db.refresh(model)
    logger.info("✅ [SDModels] Created: %s", model.name)
    return model


@router.put("/sd-models/{model_id}", response_model=SDModelResponse)
async def update_sd_model(model_id: int, data: SDModelUpdate, db: Session = Depends(get_db)):
    """Update an SD model."""
    model = db.query(SDModel).filter(SDModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="SD model not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(model, key, value)

    db.commit()
    db.refresh(model)
    logger.info("✏️ [SDModels] Updated: %s", model.name)
    return model


@router.delete("/sd-models/{model_id}", response_model=OkDeletedResponse)
async def delete_sd_model(model_id: int, db: Session = Depends(get_db)):
    """Delete an SD model."""
    model = db.query(SDModel).filter(SDModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="SD model not found")

    name = model.name
    db.delete(model)
    db.commit()
    logger.info("🗑️ [SDModels] Deleted: %s", name)
    return {"ok": True, "deleted": name}


# ============================================================
# Embeddings
# ============================================================


@router.get("/embeddings", response_model=list[EmbeddingResponse])
async def list_embeddings(
    embedding_type: str | None = None,
    base_model: str | None = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """List all embeddings."""
    query = db.query(Embedding)
    if active_only:
        query = query.filter(Embedding.is_active)
    if embedding_type:
        query = query.filter(Embedding.embedding_type == embedding_type)
    if base_model:
        query = query.filter(Embedding.base_model == base_model)
    embeddings = query.order_by(Embedding.name).all()
    logger.info("📋 [Embeddings] Listed %d embeddings", len(embeddings))
    return embeddings


@router.get("/embeddings/{embedding_id}", response_model=EmbeddingResponse)
async def get_embedding(embedding_id: int, db: Session = Depends(get_db)):
    """Get a single embedding."""
    embedding = db.query(Embedding).filter(Embedding.id == embedding_id).first()
    if not embedding:
        raise HTTPException(status_code=404, detail="Embedding not found")
    return embedding


@router.post("/embeddings", response_model=EmbeddingResponse, status_code=201)
async def create_embedding(data: EmbeddingCreate, db: Session = Depends(get_db)):
    """Create a new embedding."""
    existing = db.query(Embedding).filter(Embedding.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Embedding already exists")

    embedding = Embedding(**data.model_dump())
    db.add(embedding)
    db.commit()
    db.refresh(embedding)
    logger.info("✅ [Embeddings] Created: %s", embedding.name)
    return embedding


@router.put("/embeddings/{embedding_id}", response_model=EmbeddingResponse)
async def update_embedding(embedding_id: int, data: EmbeddingUpdate, db: Session = Depends(get_db)):
    """Update an embedding."""
    embedding = db.query(Embedding).filter(Embedding.id == embedding_id).first()
    if not embedding:
        raise HTTPException(status_code=404, detail="Embedding not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(embedding, key, value)

    db.commit()
    db.refresh(embedding)
    logger.info("✏️ [Embeddings] Updated: %s", embedding.name)
    return embedding


@router.delete("/embeddings/{embedding_id}", response_model=OkDeletedResponse)
async def delete_embedding(embedding_id: int, db: Session = Depends(get_db)):
    """Delete an embedding."""
    embedding = db.query(Embedding).filter(Embedding.id == embedding_id).first()
    if not embedding:
        raise HTTPException(status_code=404, detail="Embedding not found")

    name = embedding.name
    db.delete(embedding)
    db.commit()
    logger.info("🗑️ [Embeddings] Deleted: %s", name)
    return {"ok": True, "deleted": name}


# ============================================================
# SD WebUI Proxy (absorbed from sd.py)
# ============================================================


@router.get("/sd/models", response_model=SDWebUIModelsResponse)
async def list_sd_webui_models():
    """List models from SD WebUI."""
    logger.info("📥 [SD Models]")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(SD_MODELS_URL, timeout=SD_API_TIMEOUT)
            res.raise_for_status()
            data = res.json()
            return {"models": data if isinstance(data, list) else []}
    except httpx.HTTPError as exc:
        logger.exception("SD models fetch failed")
        raise HTTPException(status_code=502, detail="SD WebUI API error") from exc


@router.get("/sd/options", response_model=SDWebUIOptionsResponse)
async def get_sd_options():
    """Get SD WebUI options."""
    logger.info("📥 [SD Options]")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(SD_OPTIONS_URL, timeout=SD_API_TIMEOUT)
            res.raise_for_status()
            data = res.json()
            if isinstance(data, dict):
                return {"options": data, "model": data.get("sd_model_checkpoint", "Unknown")}
            return {"options": {}, "model": "Unknown"}
    except httpx.HTTPError as exc:
        logger.exception("SD options fetch failed")
        raise HTTPException(status_code=502, detail="SD WebUI API error") from exc


@router.post("/sd/options", response_model=SDWebUIOptionsUpdateResponse)
async def update_sd_options(request: SDModelRequest):
    """Update SD WebUI options (change active model)."""
    logger.info("📥 [SD Options Update] %s", request.model_dump())
    payload = {"sd_model_checkpoint": request.sd_model_checkpoint}
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(SD_OPTIONS_URL, json=payload, timeout=SD_MODEL_SWITCH_TIMEOUT)
            res.raise_for_status()
            data = res.json()
            model_name = request.sd_model_checkpoint
            if isinstance(data, dict):
                model_name = data.get("sd_model_checkpoint", request.sd_model_checkpoint)
            return {"ok": True, "model": model_name}
    except httpx.HTTPError as exc:
        logger.exception("SD options update failed")
        raise HTTPException(status_code=502, detail="SD WebUI API error") from exc


@router.get("/sd/loras", response_model=SDWebUILorasResponse)
async def list_sd_loras():
    """List LoRAs from SD WebUI."""
    logger.info("📥 [SD LoRAs]")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(SD_LORAS_URL, timeout=SD_API_TIMEOUT)
            res.raise_for_status()
            data = res.json()
            return {"loras": data if isinstance(data, list) else []}
    except httpx.HTTPError as exc:
        logger.exception("SD LoRAs fetch failed")
        raise HTTPException(status_code=502, detail="SD WebUI API error") from exc
