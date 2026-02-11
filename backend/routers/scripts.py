"""Script generation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from schemas import StoryboardRequest
from services.script.gemini_generator import generate_script

router = APIRouter(prefix="/scripts", tags=["scripts"])


@router.post("/generate")
async def generate_script_endpoint(request: StoryboardRequest, db: Session = Depends(get_db)):
    logger.info("\U0001f4dd [Script Generate] %s", request.model_dump())
    return await generate_script(request, db)
