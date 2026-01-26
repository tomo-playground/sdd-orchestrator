"""Storyboard creation endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from config import logger
from schemas import StoryboardRequest
from services.storyboard import create_storyboard

router = APIRouter(prefix="/storyboard", tags=["storyboard"])


@router.post("/create")
async def create_storyboard_endpoint(request: StoryboardRequest):
    logger.info("📥 [Storyboard Req] %s", request.model_dump())
    return create_storyboard(request)
