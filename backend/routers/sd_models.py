"""SD Model and Embedding CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from models import SDModel, Embedding
from schemas import (
    SDModelCreate,
    SDModelResponse,
    SDModelUpdate,
    EmbeddingCreate,
    EmbeddingResponse,
    EmbeddingUpdate,
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
        query = query.filter(SDModel.is_active == True)
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


@router.delete("/sd-models/{model_id}")
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
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """List all embeddings."""
    query = db.query(Embedding)
    if active_only:
        query = query.filter(Embedding.is_active == True)
    if embedding_type:
        query = query.filter(Embedding.embedding_type == embedding_type)
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


@router.delete("/embeddings/{embedding_id}")
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
