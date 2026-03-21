from __future__ import annotations

import os
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# --- Sentry Error Monitoring ---
from config import SENTRY_DSN_BACKEND, SENTRY_ENVIRONMENT, SENTRY_TRACES_SAMPLE_RATE
from routers import admin_app_router, service_app_router

if SENTRY_DSN_BACKEND:
    sentry_sdk.init(
        dsn=SENTRY_DSN_BACKEND,
        environment=SENTRY_ENVIRONMENT,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
    )


def _auto_seed_valence(db) -> None:
    """Schedule valence classification as a background asyncio task."""
    import asyncio

    from models.tag import Tag

    target_groups = ["expression", "gaze", "mood"]
    count = (
        db.query(Tag.id)
        .filter(Tag.group_name.in_(target_groups), Tag.is_active.is_(True), Tag.valence.is_(None))
        .count()
    )
    if count == 0:
        return

    from config import GEMINI_API_KEY, logger

    if not GEMINI_API_KEY:
        logger.warning("[Valence] %d tags need valence but GEMINI_API_KEY not set", count)
        return

    from routers.admin import _run_valence_classification

    logger.info("[Valence] %d unclassified tags found, seeding in background...", count)

    def _on_valence_done(t: asyncio.Task) -> None:
        if t.cancelled():
            return
        exc = t.exception()
        if exc:
            logger.error("[Valence] Background task failed: %s", exc)

    task = asyncio.create_task(_run_valence_classification(target_groups, False))
    task.add_done_callback(_on_valence_done)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize resources on startup and clean up on shutdown."""
    # Validate storage credentials before initialization
    from config import logger, validate_storage_config
    from database import engine, get_db
    from models.base import Base
    from services.keywords.db_cache import (
        LoRATriggerCache,
        TagAliasCache,
        TagCategoryCache,
        TagFilterCache,
        TagRuleCache,
        TagValenceCache,
    )
    from services.storage import initialize_storage

    validate_storage_config()

    # Initialize Storage Service
    initialize_storage()

    # Ensure repository assets are in shared storage
    from services.asset_service import AssetService

    AssetService.ensure_shared_assets()
    Base.metadata.create_all(bind=engine)

    # Initialize Tag Caches
    db = next(get_db())
    try:
        TagCategoryCache.initialize(db)
        TagFilterCache.initialize(db)
        TagAliasCache.initialize(db)
        TagRuleCache.initialize(db)
        TagValenceCache.initialize(db)
        LoRATriggerCache.initialize(db)

        # Self-Correction: Apply high-confidence tag suggestions
        from services.keywords.suggestions import apply_high_confidence_suggestions, sync_default_layers

        applied = apply_high_confidence_suggestions()
        if applied > 0:
            logger.info(f"✅ [Self-Correction] Auto-classified {applied} tags on startup")

        synced = sync_default_layers()
        if synced > 0:
            logger.info(f"✅ [Sync] Fixed {synced} stale default_layer values on startup")

        # Auto-seed valence for unclassified tags (non-blocking)
        _auto_seed_valence(db)

    except Exception as e:
        logger.error(f"Failed to initialize tag caches or self-correct: {e}")
    finally:
        db.close()

    # Audio Server health check (non-blocking, failure won't prevent startup)
    from services.audio_client import check_health

    health = await check_health()
    if health.get("status") == "ok":
        logger.info("[Audio] Audio Server is ready: %s", health)
    else:
        logger.warning("[Audio] Audio Server not ready (will retry on first request): %s", health)

    # Initialize LangGraph Checkpointer + Store
    from services.agent.checkpointer import close_checkpointer, init_checkpointer
    from services.agent.store import close_store, get_store

    await init_checkpointer()
    await get_store()

    logger.info("🚀 [Startup] Application started successfully")

    yield

    # Shutdown logic
    from services.agent.observability import flush_langfuse

    flush_langfuse()
    await close_store()
    await close_checkpointer()

    # Close Gemini client and recreate for hot-reload compatibility
    from google import genai as _genai  # noqa: PLC0415

    import config as _cfg

    if _cfg.gemini_client:
        try:
            await _cfg.gemini_client.aio.aclose()
            # Recreate client so hot-reload doesn't use a closed client
            _cfg.gemini_client = _genai.Client(api_key=_cfg.GEMINI_API_KEY) if _cfg.GEMINI_API_KEY else None
            logger.info("🛑 [Shutdown] Gemini client closed and recreated")
        except Exception as e:
            logger.warning("⚠️ [Shutdown] Gemini client close error: %s", e)

    logger.info("🛑 [Shutdown] Application execution finished")


# --- App Setup ---
app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

import logging

from config import CORS_ORIGINS  # noqa: E402
from config import logger as _logger  # noqa: E402


class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("GET /health") == -1


logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())

_cors_credentials = True
if "*" in CORS_ORIGINS:
    _logger.error(
        "CORS misconfiguration: allow_credentials=True with wildcard origin '*'. "
        "Forcing allow_credentials=False to prevent browser rejection."
    )
    _cors_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=_cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Static Files ---
os.makedirs("outputs", exist_ok=True)
app.mount("/outputs", StaticFiles(directory="outputs", html=False), name="outputs")


# --- Health Check ---
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# --- Routers (2 parent routers replace 29 individual include_router calls) ---
app.include_router(service_app_router)
app.include_router(admin_app_router)


# --- OpenAPI: split docs for Service vs Admin ---
_service_openapi_cache: dict | None = None
_admin_openapi_cache: dict | None = None


def _service_openapi() -> dict:
    global _service_openapi_cache
    if _service_openapi_cache is None:
        _service_openapi_cache = get_openapi(
            title="Shorts Producer — Service API",
            version="1.0.0",
            description="User-facing content production API",
            routes=[r for r in app.routes if getattr(r, "path", "").startswith("/api/v1")],
        )
    return _service_openapi_cache


def _admin_openapi() -> dict:
    global _admin_openapi_cache
    if _admin_openapi_cache is None:
        _admin_openapi_cache = get_openapi(
            title="Shorts Producer — Admin API",
            version="1.0.0",
            description="Back-office system management API",
            routes=[r for r in app.routes if getattr(r, "path", "").startswith("/api/admin")],
        )
    return _admin_openapi_cache


@app.get("/openapi.json", include_in_schema=False)
async def service_openapi_json():
    return JSONResponse(_service_openapi())


@app.get("/admin/openapi.json", include_in_schema=False)
async def admin_openapi_json():
    return JSONResponse(_admin_openapi())


@app.get("/docs", include_in_schema=False)
async def service_docs(_req: Request):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Service API Docs")


@app.get("/admin/docs", include_in_schema=False)
async def admin_docs(_req: Request):
    return get_swagger_ui_html(openapi_url="/admin/openapi.json", title="Admin API Docs")


if __name__ == "__main__":
    import uvicorn

    from config import SERVER_HOST, SERVER_PORT

    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
