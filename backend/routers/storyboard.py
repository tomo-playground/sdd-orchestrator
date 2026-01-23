"""Storyboard creation endpoint."""

from __future__ import annotations

from fastapi import APIRouter

import logic
from config import logger
from schemas import StoryboardRequest

router = APIRouter(prefix="/storyboard", tags=["storyboard"])


@router.post("/create")
async def create_storyboard(request: StoryboardRequest):
    logger.info("📥 [Storyboard Req] %s", request.model_dump())
    return logic.logic_create_storyboard(request)
