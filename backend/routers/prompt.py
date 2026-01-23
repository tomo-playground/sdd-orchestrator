"""Prompt manipulation endpoints."""

from __future__ import annotations

from fastapi import APIRouter

import logic
from schemas import PromptRewriteRequest, PromptSplitRequest

router = APIRouter(prefix="/prompt", tags=["prompt"])


@router.post("/rewrite")
async def rewrite_prompt(request: PromptRewriteRequest):
    logic.logger.info("📥 [Prompt Rewrite Req] %s", request.model_dump())
    return logic.logic_rewrite_prompt(request)


@router.post("/split")
async def split_prompt(request: PromptSplitRequest):
    logic.logger.info("📥 [Prompt Split Req] %s", request.model_dump())
    return logic.logic_split_prompt(request)
