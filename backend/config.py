"""Configuration and global objects for Shorts Producer Backend.

Centralizes all configuration, constants, and shared objects.
"""

from __future__ import annotations

import logging
import os
import pathlib

from dotenv import load_dotenv
from google import genai
from jinja2 import Environment, FileSystemLoader

load_dotenv()

# --- Database ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.warning("DATABASE_URL is not set. Database functionality will fail.")

# --- Logging ---
LOG_FILE = os.getenv("LOG_FILE", "logs/backend.log")
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "1").lower() not in {"0", "false", "no"}

_handlers = [logging.StreamHandler()]
if LOG_TO_FILE:
    _log_path = pathlib.Path(LOG_FILE)
    _log_path.parent.mkdir(parents=True, exist_ok=True)
    _handlers.append(logging.FileHandler(_log_path, encoding="utf-8"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=_handlers,
)

logger = logging.getLogger("backend")
if LOG_TO_FILE:
    _log_path = pathlib.Path(LOG_FILE)
    _log_path.parent.mkdir(parents=True, exist_ok=True)
    if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        _file_handler = logging.FileHandler(_log_path, encoding="utf-8")
        _file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(_file_handler)
        logger.propagate = True
        logger.info("File logging enabled: %s", _log_path)

# --- Directory Configuration ---
OUTPUT_DIR = pathlib.Path("outputs")
IMAGE_DIR = OUTPUT_DIR / "images"
VIDEO_DIR = OUTPUT_DIR / "videos"
CANDIDATE_DIR = OUTPUT_DIR / "candidates"
AVATAR_DIR = OUTPUT_DIR / "avatars"
CACHE_DIR = OUTPUT_DIR / "cache"
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "86400"))
ASSETS_DIR = pathlib.Path("assets")
AUDIO_DIR = ASSETS_DIR / "audio"
OVERLAY_DIR = ASSETS_DIR / "overlay"
FONTS_DIR = ASSETS_DIR / "fonts"
TEMPLATES_DIR = pathlib.Path("templates")

# Ensure directories exist
for _d in (OUTPUT_DIR, IMAGE_DIR, VIDEO_DIR, CANDIDATE_DIR, AVATAR_DIR, CACHE_DIR, AUDIO_DIR, OVERLAY_DIR, FONTS_DIR, TEMPLATES_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --- API Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

BASE_DIR = pathlib.Path(__file__).resolve().parent
template_env = Environment(loader=FileSystemLoader(str(BASE_DIR / TEMPLATES_DIR)))

SD_BASE_URL = os.getenv("SD_BASE_URL", "http://127.0.0.1:7860")
if SD_BASE_URL == "http://127.0.0.1:7860":
    logger.info("Using default SD_BASE_URL: %s", SD_BASE_URL)

SD_TXT2IMG_URL = f"{SD_BASE_URL}/sdapi/v1/txt2img"
SD_MODELS_URL = f"{SD_BASE_URL}/sdapi/v1/sd-models"
SD_OPTIONS_URL = f"{SD_BASE_URL}/sdapi/v1/options"
SD_LORAS_URL = f"{SD_BASE_URL}/sdapi/v1/loras"
SD_TIMEOUT_SECONDS = float(os.getenv("SD_TIMEOUT_SECONDS", "600"))

API_PUBLIC_URL = os.getenv("API_PUBLIC_URL", "http://localhost:8000").rstrip("/")
if API_PUBLIC_URL == "http://localhost:8000":
    logger.info("Using default API_PUBLIC_URL: %s", API_PUBLIC_URL)

# --- Model Configuration ---
WD14_MODEL_DIR = pathlib.Path(os.getenv("WD14_MODEL_DIR", "models/wd14"))
WD14_THRESHOLD = float(os.getenv("WD14_THRESHOLD", "0.35"))

# --- IP-Adapter Character Presets ---
# Per-character IP-Adapter settings for optimal consistency
# weight: Higher = more similar to reference (0.6-0.95)
# model: "clip" (style), "clip_face" (face+style), "faceid" (real faces only)
CHARACTER_PRESETS: dict[str, dict] = {
    # Standard anime characters - moderate weight for flexibility
    "Generic Anime Boy": {
        "weight": 0.75,
        "model": "clip_face",
        "description": "Standard anime male character",
    },
    "Generic Anime Girl": {
        "weight": 0.75,
        "model": "clip_face",
        "description": "Standard anime female character",
    },
    "Eureka": {
        "weight": 0.80,
        "model": "clip_face",
        "description": "Eureka anime character",
    },
    "Midoriya": {
        "weight": 0.80,
        "model": "clip_face",
        "description": "Midoriya anime character",
    },
    # Chibi style - higher weight to maintain proportions
    "Chibi": {
        "weight": 0.85,
        "model": "clip",
        "description": "Generic chibi style",
    },
    "Eureka Chibi": {
        "weight": 0.85,
        "model": "clip",
        "description": "Eureka in chibi style",
    },
    "Midoriya Chibi": {
        "weight": 0.85,
        "model": "clip",
        "description": "Midoriya in chibi style",
    },
    # Blindbox/3D style - highest weight for stylized look
    "Blindbox": {
        "weight": 0.90,
        "model": "clip",
        "description": "3D blindbox figure style",
    },
    "Eureka Blindbox": {
        "weight": 0.90,
        "model": "clip",
        "description": "Eureka in blindbox style",
    },
}

# Default IP-Adapter settings for unknown characters
DEFAULT_CHARACTER_PRESET = {
    "weight": 0.75,
    "model": "clip_face",
}
