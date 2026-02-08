"""Stable Diffusion WebUI proxy endpoints."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException

from config import SD_API_TIMEOUT, SD_LORAS_URL, SD_MODELS_URL, SD_OPTIONS_URL, logger
from schemas import SDModelRequest

router = APIRouter(prefix="/sd", tags=["sd"])


@router.get("/models")
async def list_sd_models():
    logger.info("📥 [SD Models]")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(SD_MODELS_URL, timeout=SD_API_TIMEOUT)
            res.raise_for_status()
            data = res.json()
            return {"models": data if isinstance(data, list) else []}
    except httpx.HTTPError as exc:
        logger.exception("SD models fetch failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/options")
async def get_sd_options():
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
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/options")
async def update_sd_options(request: SDModelRequest):
    logger.info("📥 [SD Options Update] %s", request.model_dump())
    payload = {"sd_model_checkpoint": request.sd_model_checkpoint}
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(SD_OPTIONS_URL, json=payload, timeout=SD_API_TIMEOUT)
            res.raise_for_status()
            data = res.json()
            model_name = request.sd_model_checkpoint
            if isinstance(data, dict):
                model_name = data.get("sd_model_checkpoint", request.sd_model_checkpoint)
            return {"ok": True, "model": model_name}
    except httpx.HTTPError as exc:
        logger.exception("SD options update failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/loras")
async def list_sd_loras():
    logger.info("📥 [SD LoRAs]")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(SD_LORAS_URL, timeout=SD_API_TIMEOUT)
            res.raise_for_status()
            data = res.json()
            return {"loras": data if isinstance(data, list) else []}
    except httpx.HTTPError as exc:
        logger.exception("SD LoRAs fetch failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
