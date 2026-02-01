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

# --- Base Directory ---
BASE_DIR = pathlib.Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

# --- Public URL ---
API_PUBLIC_URL = os.getenv("API_PUBLIC_URL", "http://localhost:8000")

# --- Storage Configuration ---
STORAGE_MODE = os.getenv("STORAGE_MODE", "s3")  # 's3' or 'local'
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "password123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "shorts-producer")
# Public URL for S3/MinIO assets (if different from API_PUBLIC_URL)
STORAGE_PUBLIC_URL = os.getenv("STORAGE_PUBLIC_URL", "http://localhost:9000")

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
OUTPUT_DIR = BASE_DIR / "outputs"
IMAGE_DIR = OUTPUT_DIR / "images"
VIDEO_DIR = OUTPUT_DIR / "videos"
CANDIDATE_DIR = OUTPUT_DIR / "candidates"
AVATAR_DIR = OUTPUT_DIR / "avatars"
CACHE_DIR = OUTPUT_DIR / "cache"
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "86400"))
MEDIA_ASSET_TEMP_TTL_SECONDS = int(os.getenv("MEDIA_ASSET_TEMP_TTL_SECONDS", "86400"))
ASSETS_DIR = BASE_DIR / "assets"
AUDIO_DIR = ASSETS_DIR / "audio"
OVERLAY_DIR = ASSETS_DIR / "overlay"
FONTS_DIR = ASSETS_DIR / "fonts"
TEMPLATES_DIR = BASE_DIR / "templates"

# Ensure directories exist
for _d in (OUTPUT_DIR, IMAGE_DIR, VIDEO_DIR, CANDIDATE_DIR, AVATAR_DIR, CACHE_DIR, ASSETS_DIR, AUDIO_DIR, OVERLAY_DIR, FONTS_DIR, TEMPLATES_DIR):
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

template_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

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
DEFAULT_REFERENCE_BASE_PROMPT = "masterpiece, best_quality, ultra-detailed, solo, full_body, (standing:1.2), portrait, facing_viewer, front_view, looking_at_viewer, straight_on, white_background, simple_background, plain_background, solid_background"
DEFAULT_REFERENCE_NEGATIVE_PROMPT = "lowres, (bad_anatomy:1.2), (bad_hands:1.2), text, error, missing_fingers, extra_digit, fewer_digits, cropped, worst_quality, low_quality, normal_quality, jpeg_artifacts, signature, watermark, username, blurry, easynegative, verybadimagenegative_v1.3, detailed_background, scenery, outdoors, indoors"

# Default negative prompt for scene generation (applied to Gemini-generated scenes)
DEFAULT_SCENE_NEGATIVE_PROMPT = "lowres, bad_anatomy, bad_hands, text, error, missing_fingers, extra_digit, fewer_digits, cropped, worst_quality, low_quality, jpeg_artifacts, signature, watermark, username, blurry, easynegative, verybadimagenegative_v1.3"

# --- Gemini Auto Edit Configuration (Phase 6-4.22) ---
# Master switch: Enable automatic image editing with Gemini when match_rate is low
# WARNING: This feature incurs API costs (~$0.04 per edit)
# Default: False (must be explicitly enabled)
GEMINI_AUTO_EDIT_ENABLED = os.getenv("GEMINI_AUTO_EDIT_ENABLED", "false").lower() == "true"

# Match Rate threshold for triggering auto-edit (0.0 ~ 1.0)
# Images with match_rate < threshold will be automatically edited
# Lower = more edits, Higher = fewer edits
GEMINI_AUTO_EDIT_THRESHOLD = float(os.getenv("GEMINI_AUTO_EDIT_THRESHOLD", "0.7"))

# Maximum cost per storyboard (USD)
# Auto-edit will stop if total Gemini edit cost exceeds this limit
GEMINI_AUTO_EDIT_MAX_COST_PER_STORYBOARD = float(os.getenv("GEMINI_AUTO_EDIT_MAX_COST", "1.0"))

# Maximum retry count per scene
# Prevents infinite edit loops on problematic scenes
GEMINI_AUTO_EDIT_MAX_RETRIES_PER_SCENE = int(os.getenv("GEMINI_AUTO_EDIT_MAX_RETRIES", "1"))

# Log startup status
logger.info(
    "Gemini Auto Edit: %s (threshold=%.2f, max_cost=$%.2f, max_retries=%d)",
    "ENABLED" if GEMINI_AUTO_EDIT_ENABLED else "DISABLED",
    GEMINI_AUTO_EDIT_THRESHOLD,
    GEMINI_AUTO_EDIT_MAX_COST_PER_STORYBOARD,
    GEMINI_AUTO_EDIT_MAX_RETRIES_PER_SCENE,
)

# --- FFmpeg / Video Encoding Defaults ---
# Output video FPS (used by zoompan, encoding, and frame calculations)
VIDEO_FPS = int(os.getenv("VIDEO_FPS", "30"))
# H.264 Constant Rate Factor (0=lossless, 18=visually lossless, 23=default, 51=worst)
VIDEO_CRF = int(os.getenv("VIDEO_CRF", "20"))
# x264 encoding preset (ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow)
VIDEO_PRESET = os.getenv("VIDEO_PRESET", "medium")
# Video codec
VIDEO_CODEC = os.getenv("VIDEO_CODEC", "libx264")
# Pixel format (yuv420p for maximum compatibility)
VIDEO_PIX_FMT = os.getenv("VIDEO_PIX_FMT", "yuv420p")
# Audio codec and bitrate
AUDIO_CODEC = os.getenv("AUDIO_CODEC", "aac")
AUDIO_BITRATE = os.getenv("AUDIO_BITRATE", "192k")
# FFmpeg subprocess timeout in seconds (prevents infinite hangs)
FFMPEG_TIMEOUT_SECONDS = int(os.getenv("FFMPEG_TIMEOUT_SECONDS", "600"))

# --- IP-Adapter Defaults ---
# Default IP-Adapter settings (per-character overrides stored in DB)
# weight=0.35: POC 30-scene 실험 검증값 (clip_face + no BREAK 최적)
DEFAULT_CHARACTER_PRESET = {
    "weight": 0.35,
    "model": "clip_face",
}
