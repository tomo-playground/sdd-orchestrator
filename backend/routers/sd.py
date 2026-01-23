"""Stable Diffusion WebUI proxy endpoints."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException

import logic
from schemas import SDModelRequest

router = APIRouter(prefix="/sd", tags=["sd"])


@router.get("/models")
async def list_sd_models():
    logic.logger.info("📥 [SD Models]")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(logic.SD_MODELS_URL, timeout=10.0)
            res.raise_for_status()
            data = res.json()
            return {"models": data if isinstance(data, list) else []}
    except httpx.HTTPError as exc:
        logic.logger.exception("SD models fetch failed")
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/options")
async def get_sd_options():
    logic.logger.info("📥 [SD Options]")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(logic.SD_OPTIONS_URL, timeout=10.0)
            res.raise_for_status()
            data = res.json()
            if isinstance(data, dict):
                return {"options": data, "model": data.get("sd_model_checkpoint", "Unknown")}
            return {"options": {}, "model": "Unknown"}
    except httpx.HTTPError as exc:
        logic.logger.exception("SD options fetch failed")
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/options")
async def update_sd_options(request: SDModelRequest):
    logic.logger.info("📥 [SD Options Update] %s", request.model_dump())
    payload = {"sd_model_checkpoint": request.sd_model_checkpoint}
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(logic.SD_OPTIONS_URL, json=payload, timeout=10.0)
            res.raise_for_status()
            data = res.json()
            return {"ok": True, "model": data.get("sd_model_checkpoint", request.sd_model_checkpoint)}
    except httpx.HTTPError as exc:
        logic.logger.exception("SD options update failed")
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/loras")
async def list_sd_loras():
    logic.logger.info("📥 [SD LoRAs]")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(logic.SD_LORAS_URL, timeout=10.0)
            res.raise_for_status()
            data = res.json()
            return {"loras": data if isinstance(data, list) else []}
    except httpx.HTTPError as exc:
        logic.logger.exception("SD LoRAs fetch failed")
        raise HTTPException(status_code=502, detail=str(exc))
