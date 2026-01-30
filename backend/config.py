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

# --- Logging ---
LOG_FILE = os.getenv("LOG_FILE", "logs/backend.log")
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "1").lower() not in {"0", "false", "no"}
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

_handlers = [logging.StreamHandler()]
if LOG_TO_FILE:
    _log_path = pathlib.Path(LOG_FILE)
    _log_path.parent.mkdir(parents=True, exist_ok=True)
    _handlers.append(logging.FileHandler(_log_path, encoding="utf-8"))

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
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

# --- Database ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.warning("DATABASE_URL is not set. Database functionality will fail.")

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
# Gemini Image Generation Model (Nano Banana = gemini-2.5-flash-image)
# Optimized for speed and cost. Alternative: gemini-3-pro-image-preview (Nano Banana Pro)
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
# Gemini Text/Vision Model (Standard = gemini-2.0-flash)
# Used for storyboard generation, prompt rewriting, and vision analysis
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.0-flash")

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

# --- Image Generation Defaults ---
# Optimized for Speed + Quality + Post/Full compatibility
# 512x768 (2:3) allows perfect 1:1 top-crop and full 9:16 cover
SD_DEFAULT_WIDTH = int(os.getenv("SD_DEFAULT_WIDTH", "512"))
SD_DEFAULT_HEIGHT = int(os.getenv("SD_DEFAULT_HEIGHT", "768"))

API_PUBLIC_URL = os.getenv("API_PUBLIC_URL", "http://localhost:8000").rstrip("/")
if API_PUBLIC_URL == "http://localhost:8000":
    logger.info("Using default API_PUBLIC_URL: %s", API_PUBLIC_URL)

# --- Model Configuration ---
WD14_MODEL_DIR = pathlib.Path(os.getenv("WD14_MODEL_DIR", "models/wd14"))
WD14_THRESHOLD = float(os.getenv("WD14_THRESHOLD", "0.35"))

# --- Tag Effectiveness Configuration ---
# Threshold for filtering low-effectiveness tags in Gemini prompts
# Tags with effectiveness < threshold are excluded from recommendations
# effectiveness = match_count / use_count (WD14 detection rate)
TAG_EFFECTIVENESS_THRESHOLD = float(os.getenv("TAG_EFFECTIVENESS_THRESHOLD", "0.3"))
# Minimum usage count to consider effectiveness data reliable
TAG_MIN_USE_COUNT_FOR_FILTERING = int(os.getenv("TAG_MIN_USE_COUNT_FOR_FILTERING", "3"))

# --- Tag Recommendation Configuration (Phase 6-4-21 Task #8) ---
# High-performance tags shown in "Recommended" section of Gemini prompts
# Threshold for marking tags as "recommended" (0.8 = 80%+ success rate)
RECOMMENDATION_EFFECTIVENESS_THRESHOLD = float(
    os.getenv("RECOMMENDATION_EFFECTIVENESS_THRESHOLD", "0.8")
)
# Minimum usage count for reliable recommendation data
RECOMMENDATION_MIN_USE_COUNT = int(os.getenv("RECOMMENDATION_MIN_USE_COUNT", "10"))

# --- Danbooru Validation Configuration ---
# Enable Danbooru API validation for unknown tags (Phase 2)
# When enabled, tags not in DB are validated against Danbooru API
# This adds 2-5s for first-time tags, but ensures 95%+ accuracy
ENABLE_DANBOORU_VALIDATION = os.getenv("ENABLE_DANBOORU_VALIDATION", "true").lower() == "true"

# --- Reference Image Generation Defaults ---
# Default prompts for generating IP-Adapter reference images
# Used when creating new characters without custom reference prompts
DEFAULT_REFERENCE_BASE_PROMPT = "masterpiece, best_quality, ultra-detailed, solo, upper_body, portrait, facing_viewer, front_view, looking_at_viewer, straight_on, white_background, simple_background, plain_background, solid_background"
DEFAULT_REFERENCE_NEGATIVE_PROMPT = "lowres, (bad_anatomy:1.2), (bad_hands:1.2), text, error, missing_fingers, extra_digit, fewer_digits, cropped, worst_quality, low_quality, normal_quality, jpeg_artifacts, signature, watermark, username, blurry, easynegative, verybadimagenegative_v1.3, detailed_background, scenery, outdoors, indoors"

# Default negative prompt for scene generation (applied to Gemini-generated scenes)
DEFAULT_SCENE_NEGATIVE_PROMPT = "lowres, bad_anatomy, bad_hands, text, error, missing_fingers, extra_digit, fewer_digits, cropped, worst_quality, low_quality, jpeg_artifacts, signature, watermark, username, blurry, easynegative, verybadimagenegative_v1.3"

# --- IP-Adapter Character Presets ---
# Per-character IP-Adapter settings for optimal consistency
# weight: Higher = more similar to reference (0.6-0.95)
# model: "clip" (style), "clip_face" (face+style), "faceid" (real faces only)
# --- IP-Adapter Character Presets ---
# Legacy presets removed. Now fully managed via database (Character model).
CHARACTER_PRESETS: dict[str, dict] = {}

# Default IP-Adapter settings for unknown characters
DEFAULT_CHARACTER_PRESET = {
    "weight": 0.75,
    "model": "clip_face",
}
