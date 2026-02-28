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

# --- Storage Configuration ---
STORAGE_MODE = os.getenv("STORAGE_MODE", "s3")  # 's3' or 'local'
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "shorts-producer")
# Public URL for S3/MinIO assets (if different from API_PUBLIC_URL)
STORAGE_PUBLIC_URL = os.getenv("STORAGE_PUBLIC_URL", "http://localhost:9000")

# --- Logging ---
LOG_FILE = os.getenv("LOG_FILE", "logs/backend.log")
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "1").lower() not in {"0", "false", "no"}
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

_handlers: list[logging.Handler] = [logging.StreamHandler()]
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
# propagate=True (default): root logger's handlers (StreamHandler + FileHandler) handle all output.
# Do NOT add a separate FileHandler here — it causes duplicate log entries in the log file.

# --- Database ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.warning("DATABASE_URL is not set. Database functionality will fail.")

# --- Directory Configuration ---
OUTPUT_DIR = BASE_DIR / "outputs"
IMAGE_DIR = OUTPUT_DIR / "images"
VIDEO_DIR = OUTPUT_DIR / "videos"
BUILD_DIR = OUTPUT_DIR / "_build"
PROMPT_CACHE_DIR = OUTPUT_DIR / "_prompt_cache"
S3_CACHE_DIR = OUTPUT_DIR / "_s3_cache"
AVATAR_DIR = OUTPUT_DIR / "shared" / "avatars"
# Backward-compatible alias (existing code importing CACHE_DIR keeps working)
CACHE_DIR = PROMPT_CACHE_DIR
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "86400"))
MEDIA_ASSET_TEMP_TTL_SECONDS = int(os.getenv("MEDIA_ASSET_TEMP_TTL_SECONDS", "86400"))
ASSETS_DIR = BASE_DIR / "assets"
AUDIO_DIR = ASSETS_DIR / "audio"
OVERLAY_DIR = ASSETS_DIR / "overlay"
FONTS_DIR = ASSETS_DIR / "fonts"
TEMPLATES_DIR = BASE_DIR / "templates"

# Ensure directories exist
for _d in (
    OUTPUT_DIR,
    IMAGE_DIR,
    VIDEO_DIR,
    BUILD_DIR,
    PROMPT_CACHE_DIR,
    S3_CACHE_DIR,
    AVATAR_DIR,
    ASSETS_DIR,
    AUDIO_DIR,
    OVERLAY_DIR,
    FONTS_DIR,
    TEMPLATES_DIR,
):
    _d.mkdir(parents=True, exist_ok=True)

# --- API Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
# Gemini Image Generation Model (Nano Banana = gemini-2.5-flash-image)
# Optimized for speed and cost. Alternative: gemini-3-pro-image-preview (Nano Banana Pro)
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
# Gemini Text/Vision Model (Standard = gemini-2.5-flash)
# Used for storyboard generation, prompt rewriting, and vision analysis
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
# Gemini Classifier Model — 태그 분류 전용 (lightweight, 항상 Flash 사용)
GEMINI_CLASSIFIER_MODEL = os.getenv("GEMINI_CLASSIFIER_MODEL", "gemini-2.5-flash")
GEMINI_CLASSIFIER_TIMEOUT_MS = int(os.getenv("GEMINI_CLASSIFIER_TIMEOUT_MS", "30000"))

template_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

SD_BASE_URL = os.getenv("SD_BASE_URL", "http://127.0.0.1:7860")
if SD_BASE_URL == "http://127.0.0.1:7860":
    logger.info("Using default SD_BASE_URL: %s", SD_BASE_URL)

# --- Audio Server (TTS + MusicGen sidecar) ---
AUDIO_SERVER_URL = os.getenv("AUDIO_SERVER_URL", "http://127.0.0.1:8001")
AUDIO_TIMEOUT_SECONDS = float(os.getenv("AUDIO_TIMEOUT_SECONDS", "180"))
MUSIC_TIMEOUT_SECONDS = float(os.getenv("MUSIC_TIMEOUT_SECONDS", "600"))  # 10min for MusicGen

SD_TXT2IMG_URL = f"{SD_BASE_URL}/sdapi/v1/txt2img"
SD_MODELS_URL = f"{SD_BASE_URL}/sdapi/v1/sd-models"
SD_OPTIONS_URL = f"{SD_BASE_URL}/sdapi/v1/options"
SD_LORAS_URL = f"{SD_BASE_URL}/sdapi/v1/loras"
SD_TIMEOUT_SECONDS = float(os.getenv("SD_TIMEOUT_SECONDS", "600"))
SD_BATCH_CONCURRENCY = int(os.getenv("SD_BATCH_CONCURRENCY", "3"))

# --- Image Generation Defaults ---
# Optimized for Speed + Quality + Post/Full compatibility
# 512x768 (2:3) allows perfect 1:1 top-crop and full 9:16 cover
SD_DEFAULT_WIDTH = int(os.getenv("SD_DEFAULT_WIDTH", "512"))
SD_DEFAULT_HEIGHT = int(os.getenv("SD_DEFAULT_HEIGHT", "768"))
SD_DEFAULT_STEPS = int(os.getenv("SD_DEFAULT_STEPS", "28"))
SD_DEFAULT_CFG_SCALE = float(os.getenv("SD_DEFAULT_CFG_SCALE", "7.0"))
SD_DEFAULT_SAMPLER = os.getenv("SD_DEFAULT_SAMPLER", "DPM++ 2M Karras")
SD_DEFAULT_CLIP_SKIP = int(os.getenv("SD_DEFAULT_CLIP_SKIP", "2"))

# --- LoRA Weight Cap ---
# Maximum weight for style LoRAs (applied to both character and narrator scenes)
STYLE_LORA_WEIGHT_CAP = float(os.getenv("STYLE_LORA_WEIGHT_CAP", "0.76"))

# --- SD API Timeouts ---
SD_API_TIMEOUT = float(os.getenv("SD_API_TIMEOUT", "10"))
SD_MODEL_SWITCH_TIMEOUT = float(os.getenv("SD_MODEL_SWITCH_TIMEOUT", "120"))

# --- ControlNet Timeouts ---
CONTROLNET_API_TIMEOUT = float(os.getenv("CONTROLNET_API_TIMEOUT", "10"))
CONTROLNET_GENERATE_TIMEOUT = float(os.getenv("CONTROLNET_GENERATE_TIMEOUT", "180"))
CONTROLNET_DETECT_TIMEOUT = float(os.getenv("CONTROLNET_DETECT_TIMEOUT", "60"))
# Default sampler for ControlNet-only generation (not using StyleProfile)
CONTROLNET_DEFAULT_SAMPLER = os.getenv("CONTROLNET_DEFAULT_SAMPLER", "Euler a")

# --- Character Reference Generation ---
SD_REFERENCE_STEPS = int(os.getenv("SD_REFERENCE_STEPS", "25"))
SD_REFERENCE_CFG_SCALE = float(os.getenv("SD_REFERENCE_CFG_SCALE", "7.0"))  # Lowered from 9.0 for softer colors
SD_REFERENCE_HR_UPSCALER = os.getenv("SD_REFERENCE_HR_UPSCALER", "R-ESRGAN 4x+ Anime6B")
SD_REFERENCE_DENOISING = float(os.getenv("SD_REFERENCE_DENOISING", "0.35"))
# ControlNet pose for character reference images (standing = single full-body)
SD_REFERENCE_CONTROLNET_POSE = os.getenv("SD_REFERENCE_CONTROLNET_POSE", "standing")
SD_REFERENCE_CONTROLNET_WEIGHT = float(os.getenv("SD_REFERENCE_CONTROLNET_WEIGHT", "0.8"))
SD_REFERENCE_CONTROLNET_MODE = os.getenv("SD_REFERENCE_CONTROLNET_MODE", "ControlNet is more important")
# Number of candidate images to generate for character preview selection
SD_REFERENCE_NUM_CANDIDATES = int(os.getenv("SD_REFERENCE_NUM_CANDIDATES", "3"))
# Character LoRA weight multiplier for reference images (identity hint only)
# 0.4: balanced between character identity and pose freedom (reviewed 2026-02)
REFERENCE_LORA_SCALE = float(os.getenv("REFERENCE_LORA_SCALE", "0.4"))
# Style LoRA weight multiplier for reference images
# 0.5: prevent style LoRA from producing character sheets/multiple views
REFERENCE_STYLE_LORA_SCALE = float(os.getenv("REFERENCE_STYLE_LORA_SCALE", "0.3"))

# --- External API ---
DANBOORU_API_BASE = os.getenv("DANBOORU_API_BASE", "https://danbooru.donmai.us")
DANBOORU_USER_AGENT = os.getenv("DANBOORU_USER_AGENT", "ShortsProducer/1.0")
DANBOORU_API_TIMEOUT = float(os.getenv("DANBOORU_API_TIMEOUT", "3"))
CIVITAI_API_BASE = os.getenv("CIVITAI_API_BASE", "https://civitai.com/api/v1")
CIVITAI_API_TIMEOUT = float(os.getenv("CIVITAI_API_TIMEOUT", "10"))

# --- Tag Thumbnail (Phase 15-B) ---
TAG_THUMBNAIL_WIDTH = int(os.getenv("TAG_THUMBNAIL_WIDTH", "150"))
TAG_THUMBNAIL_QUALITY = int(os.getenv("TAG_THUMBNAIL_QUALITY", "80"))
TAG_THUMBNAIL_BATCH_DELAY_MS = int(os.getenv("TAG_THUMBNAIL_BATCH_DELAY_MS", "600"))

# --- Checkpoint GC ---
CHECKPOINT_GC_RETENTION_DAYS = int(os.getenv("CHECKPOINT_GC_RETENTION_DAYS", "7"))

# --- Font & LoRA Defaults ---
DEFAULT_SCENE_TEXT_FONT = os.getenv("DEFAULT_SCENE_TEXT_FONT", "온글잎 박다현체.ttf")
DEFAULT_LORA_WEIGHT = float(os.getenv("DEFAULT_LORA_WEIGHT", "0.7"))

# --- Storyboard Defaults ---
DEFAULT_STRUCTURE = "Monologue"  # Options: "Monologue", "Dialogue"
DEFAULT_SPEAKER = "Narrator"  # Default speaker for scenes
SPEAKER_A = "A"  # Dialogue speaker A
SPEAKER_B = "B"  # Dialogue speaker B

# --- CORS Configuration ---
CORS_ORIGINS: list[str] = [
    origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()
]

SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

API_PUBLIC_URL = os.getenv("API_PUBLIC_URL", "http://localhost:8000").rstrip("/")
if API_PUBLIC_URL == "http://localhost:8000":
    logger.info("Using default API_PUBLIC_URL: %s", API_PUBLIC_URL)

# --- Model Configuration ---
WD14_MODEL_DIR = pathlib.Path(os.getenv("WD14_MODEL_DIR", "models/wd14"))
WD14_THRESHOLD = float(os.getenv("WD14_THRESHOLD", "0.35"))
# Threshold for critical failure detection (gender swap, no subject, count mismatch)
# Higher than WD14_THRESHOLD to minimize false positives on subject tags
CRITICAL_FAILURE_SUBJECT_THRESHOLD = float(os.getenv("CRITICAL_FAILURE_SUBJECT_THRESHOLD", "0.7"))

# Tags that WD14 cannot detect (style, quality, lighting, mood, abstract composition)
# These are excluded from match_rate calculation and reported as "skipped"
WD14_UNMATCHABLE_TAGS: set[str] = {
    # Style / rendering
    "flat_color",
    "cel_shading",
    "watercolor",
    "oil_painting",
    "sketch",
    "lineart",
    "monochrome",
    "greyscale",
    # Quality
    "masterpiece",
    "best_quality",
    "high_quality",
    "normal_quality",
    "worst_quality",
    "absurdres",
    "incredibly_absurdres",
    "highres",
    # Lighting
    "soft_lighting",
    "natural_light",
    "natural_lighting",
    "dramatic_lighting",
    "volumetric_lighting",
    "beautiful_lighting",
    # Mood / time of day
    "peaceful",
    "romantic",
    "mysterious",
    "morning",
    "night",
    "dawn",
    "dusk",
    "evening",
    # Abstract composition
    "dynamic_angle",
    "cinematic_composition",
    # Conceptual / not in WD14 model
    "anime_style",
    "bishounen",
    "anime_coloring",
}

# Character-identity categories exempt from effectiveness filtering.
# WD14 may under-detect these in stylised anime art, but removing them
# from prompts breaks character consistency (→ "death spiral").
# Tags are resolved lazily from CATEGORY_PATTERNS on first access.
# Tag groups where WD14 can reliably detect presence/absence.
# Used by compute_adjusted_match_rate() to exclude non-detectable groups
# (camera, lighting, mood, location, etc.) from the match rate denominator.
WD14_DETECTABLE_GROUPS: frozenset[str] = frozenset(
    {
        "subject",  # 1girl, solo — 0.9+ confidence
        "hair_color",  # black_hair, blonde_hair
        "hair_length",  # long_hair, short_hair — 최고 감지율 0.683
        "hair_style",  # ponytail, twintails — 구조적 특징
        "hair_accessory",  # hairclip, hairband — 시각적 개체
        "eye_color",  # blue_eyes, red_eyes
        # clothing 계열 (기존 "clothing" 세분화)
        "clothing_top",  # shirt, jacket
        "clothing_bottom",  # skirt, pants
        "clothing_outfit",  # dress, uniform — 0.529
        "clothing_detail",  # long_sleeves, frills
        "legwear",  # thighhighs, stockings
        "footwear",  # boots, sneakers
        "accessory",  # glasses, hat, earrings
        "expression",  # smile, open_mouth — 0.217
        "gaze",  # looking_at_viewer, closed_eyes
        "pose",  # standing, sitting — 0.300
        # action 계열 (기존 "action" 세분화)
        "action_body",  # walking, running
        "action_hand",  # holding, grabbing — 0.343
        "action_daily",  # reading, eating
        "body_feature",  # cat_ears, wings — 시각적 특징
        "appearance",  # freckles, makeup
        "body_type",  # slim, muscular — 체형
    }
)

WD14_IDENTITY_CATEGORIES: frozenset[str] = frozenset({"hair_color", "eye_color"})

# --- Auto-Regeneration (Phase 16-C) ---
AUTO_REGEN_MAX_RETRIES = int(os.getenv("AUTO_REGEN_MAX_RETRIES", "2"))
AUTO_REGEN_ENABLED = os.getenv("AUTO_REGEN_ENABLED", "true").lower() == "true"

# Character-identity groups for identity_score calculation.
# Subset of WD14_DETECTABLE_GROUPS focused on visual identity (clothing excluded —
# Scene Clothing Override changes it per scene, so it's not a fixed identity trait).
IDENTITY_SCORE_GROUPS: frozenset[str] = frozenset(
    {
        "hair_color",
        "eye_color",
        "hair_length",
        "hair_style",
        "skin_color",
        "body_feature",
        "appearance",
        "body_type",
    }
)
# Group-level weights for cross-scene consistency drift calculation (Phase 16-D).
# Higher weight = more visually impactful when drift occurs.
IDENTITY_GROUP_WEIGHTS: dict[str, float] = {
    "hair_color": 1.0,
    "eye_color": 0.8,
    "hair_length": 0.7,
    "hair_style": 0.7,
    "appearance": 0.5,
    "body_type": 0.6,
    "body_feature": 0.4,
    "skin_color": 0.3,
}

_WD14_IDENTITY_TAGS: set[str] | None = None


def get_wd14_identity_tags() -> set[str]:
    """Return the merged set of tags belonging to WD14_IDENTITY_CATEGORIES."""
    global _WD14_IDENTITY_TAGS  # noqa: PLW0603
    if _WD14_IDENTITY_TAGS is None:
        from services.keywords.patterns import CATEGORY_PATTERNS

        _WD14_IDENTITY_TAGS = set()
        for cat in WD14_IDENTITY_CATEGORIES:
            _WD14_IDENTITY_TAGS.update(CATEGORY_PATTERNS.get(cat, []))
    return _WD14_IDENTITY_TAGS


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
RECOMMENDATION_EFFECTIVENESS_THRESHOLD = float(os.getenv("RECOMMENDATION_EFFECTIVENESS_THRESHOLD", "0.8"))
# Minimum usage count for reliable recommendation data
RECOMMENDATION_MIN_USE_COUNT = int(os.getenv("RECOMMENDATION_MIN_USE_COUNT", "10"))

# --- Danbooru Validation Configuration ---
# Enable Danbooru API validation for unknown tags (Phase 2)
# When enabled, tags not in DB are validated against Danbooru API
# This adds 2-5s for first-time tags, but ensures 95%+ accuracy
ENABLE_DANBOORU_VALIDATION = os.getenv("ENABLE_DANBOORU_VALIDATION", "true").lower() == "true"

# --- Quality Tag Fallback (used when StyleProfile provides no quality tags) ---
FALLBACK_QUALITY_TAGS: list[str] = ["masterpiece", "best_quality"]

# --- V3 Prompt Composition Constants (extracted to config_prompt.py) ---
from config_prompt import *  # noqa: E402, F401, F403

# --- Reference Image Generation Defaults ---
# Default prompts for generating IP-Adapter reference images
# Used when creating new characters without custom reference prompts
DEFAULT_REFERENCE_BASE_PROMPT = ", ".join(
    [
        "masterpiece",
        "best_quality",
        "ultra-detailed",
        "(solo:1.5)",
        "full_body",
        "(standing:1.2)",
        "portrait",
        "facing_viewer",
        "front_view",
        "looking_at_viewer",
        "straight_on",
        "(white_background:1.3)",
        "(simple_background:1.3)",
        "plain_background",
        "solid_background",
        "soft_lighting",
        "natural_colors",
    ]
)
DEFAULT_REFERENCE_NEGATIVE_PROMPT = ", ".join(
    [
        "lowres",
        "(bad_anatomy:1.2)",
        "(bad_hands:1.2)",
        "text",
        "error",
        "missing_fingers",
        "extra_digit",
        "fewer_digits",
        "cropped",
        "worst_quality",
        "low_quality",
        "normal_quality",
        "jpeg_artifacts",
        "signature",
        "watermark",
        "username",
        "blurry",
        # --- 배경 억제 (강화) ---
        "(detailed_background:1.8)",
        "(scenery:1.5)",
        "(outdoors:1.5)",
        "(indoors:1.5)",
        "(ornate:1.3)",
        "(pattern:1.3)",
        "(decorative_background:1.5)",
        "(gradient_background:1.5)",
        "(abstract_background:1.5)",
        "(colorful_background:1.5)",
        "(grey_background:1.3)",
        "(black_background:1.3)",
        "border",
        "frame",
        "shadow",
        # --- 멀티뷰 억제 ---
        "(multiple_views:1.8)",
        "(character_sheet:1.8)",
        "(reference_sheet:1.5)",
        "(turnaround:1.5)",
        "(multiple_persona:1.5)",
        "(2boys:1.3)",
        "(2girls:1.3)",
        "(multiple_boys:1.3)",
        "(multiple_girls:1.3)",
    ]
)

# Default negative prompt for scene generation (applied to Gemini-generated scenes)
DEFAULT_SCENE_NEGATIVE_PROMPT = "lowres, bad_anatomy, bad_hands, text, error, missing_fingers, extra_digit, fewer_digits, cropped, worst_quality, low_quality, jpeg_artifacts, signature, watermark, username, blurry"

# Extra negative tags appended for Narrator scenes (no_humans) to suppress character generation
NARRATOR_NEGATIVE_PROMPT_EXTRA = "1girl, 1boy, 2girls, 2boys, multiple_girls, multiple_boys, person, human, male, female, solo, couple, face, portrait, upper_body, cowboy_shot"

# Stage Workflow status values (Phase 18)
STAGE_STATUS_PENDING = "pending"
STAGE_STATUS_STAGING = "staging"
STAGE_STATUS_STAGED = "staged"
STAGE_STATUS_FAILED = "failed"

# Reference AdaIN — environment atmosphere transfer (replaces Canny for BG pinning)
# Transfers color statistics (mean/variance) only, no spatial structure
REFERENCE_ADAIN_WEIGHT = float(os.getenv("REFERENCE_ADAIN_WEIGHT", "0.35"))
REFERENCE_ADAIN_WEIGHT_INDOOR = float(os.getenv("REFERENCE_ADAIN_WEIGHT_INDOOR", "0.40"))
REFERENCE_ADAIN_WEIGHT_OUTDOOR = float(os.getenv("REFERENCE_ADAIN_WEIGHT_OUTDOOR", "0.25"))
REFERENCE_ADAIN_GUIDANCE_END = float(os.getenv("REFERENCE_ADAIN_GUIDANCE_END", "0.5"))

# Default pose/gaze/expression for ControlNet when Gemini omits context_tags
DEFAULT_POSE_TAG = "standing"
DEFAULT_GAZE_TAG = "looking_at_viewer"
DEFAULT_EXPRESSION_TAG = "smile"

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


class _RuntimeSettings:
    """Mutable runtime settings for single-process use.

    Use this instead of mutating module-level constants directly.
    Reset to env-based defaults on server restart.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        """Reload all values from environment variables."""
        self.auto_edit_enabled = os.getenv("GEMINI_AUTO_EDIT_ENABLED", "false").lower() == "true"
        self.auto_edit_threshold = float(os.getenv("GEMINI_AUTO_EDIT_THRESHOLD", "0.7"))
        self.auto_edit_max_cost = float(os.getenv("GEMINI_AUTO_EDIT_MAX_COST", "1.0"))
        self.auto_edit_max_retries = int(os.getenv("GEMINI_AUTO_EDIT_MAX_RETRIES", "1"))


runtime_settings = _RuntimeSettings()

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
FFMPEG_TIMEOUT_SECONDS = int(os.getenv("FFMPEG_TIMEOUT_SECONDS", "1200"))
RENDER_TASK_TTL_SECONDS = int(os.getenv("RENDER_TASK_TTL_SECONDS", "1800"))

# --- Text Extraction Defaults ---
CAPTION_MAX_LENGTH = int(os.getenv("CAPTION_MAX_LENGTH", "60"))

# --- Per-Scene Generation Defaults (SSOT) ---
# Global defaults for per-scene generation flags.
# Finalize node uses these when auto-populating scene flags.
# Frontend receives via /presets API → generation_defaults.
DEFAULT_USE_CONTROLNET = True
DEFAULT_CONTROLNET_WEIGHT = 0.8
DEFAULT_USE_IP_ADAPTER = False
DEFAULT_IP_ADAPTER_WEIGHT = 0.7
DEFAULT_MULTI_GEN_ENABLED = False

# --- IP-Adapter Defaults ---
# Default IP-Adapter settings (per-character overrides stored in DB)
# weight=0.35: POC 30-scene 실험 검증값 (clip_face + no BREAK 최적)
DEFAULT_CHARACTER_PRESET = {
    "weight": 0.35,
    "model": "clip_face",
}

# IP-Adapter guidance defaults (per-model type)
DEFAULT_IP_ADAPTER_GUIDANCE_START = 0.0
DEFAULT_IP_ADAPTER_GUIDANCE_END_FACEID = 0.85  # Reduce prompt interference in later steps
DEFAULT_IP_ADAPTER_GUIDANCE_END_CLIP = 1.0  # Full guidance for CLIP-based models

# IP-Adapter Dual Unit (opt-in, VRAM 2x)
IP_ADAPTER_DUAL_ENABLED = os.getenv("IP_ADAPTER_DUAL_ENABLED", "false").lower() == "true"
IP_ADAPTER_DUAL_PRIMARY_RATIO = 0.7
IP_ADAPTER_DUAL_SECONDARY_RATIO = 0.3

# --- Seed Anchoring ---
SEED_ANCHOR_OFFSET = int(os.getenv("SEED_ANCHOR_OFFSET", "1000"))

# --- Image Generation Cache ---
SD_IMAGE_CACHE_ENABLED = os.getenv("SD_IMAGE_CACHE_ENABLED", "false").lower() == "true"
SD_IMAGE_CACHE_DIR = PROMPT_CACHE_DIR / "sd_images"
SD_IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
SD_IMAGE_CACHE_MAX_SIZE_MB = int(os.getenv("SD_IMAGE_CACHE_MAX_SIZE_MB", "2048"))

# FaceID face tag suppression
FACEID_SUPPRESS_TAGS: set[str] = {
    # Hair color
    "black_hair",
    "brown_hair",
    "blonde_hair",
    "red_hair",
    "blue_hair",
    "green_hair",
    "pink_hair",
    "purple_hair",
    "white_hair",
    "grey_hair",
    "silver_hair",
    "orange_hair",
    "light_brown_hair",
    # Eye color
    "blue_eyes",
    "brown_eyes",
    "green_eyes",
    "red_eyes",
    "purple_eyes",
    "yellow_eyes",
    "black_eyes",
    "grey_eyes",
    "heterochromia",
    # Face features
    "freckles",
    "mole",
    "scar",
    "facial_mark",
}
FACEID_SUPPRESS_WEIGHT = 0.3

# Reference quality validation thresholds
REFERENCE_MIN_RESOLUTION = 256
REFERENCE_MIN_FACE_RATIO = 0.10  # Face must be at least 10% of image area

# --- TTS Configuration ---
TTS_DEFAULT_LANGUAGE = os.getenv("TTS_DEFAULT_LANGUAGE", "korean")

# --- Voice Preset Configuration ---
VOICE_PRESET_MAX_FILE_SIZE = int(os.getenv("VOICE_PRESET_MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # 10MB
VOICE_PRESET_MIN_DURATION = float(os.getenv("VOICE_PRESET_MIN_DURATION", "3.0"))
VOICE_PRESET_MAX_DURATION = float(os.getenv("VOICE_PRESET_MAX_DURATION", "60.0"))
VOICE_PRESET_ALLOWED_FORMATS = {"wav", "mp3", "flac", "ogg"}

# --- TTS Naturalness ---
# Appended to every TTS instruct to reduce robotic/AI-sounding output.
# Empty string = disabled. Applies to all TTS calls (scene rendering + voice preview).
TTS_NATURALNESS_SUFFIX = os.getenv(
    "TTS_NATURALNESS_SUFFIX",
    "with natural, human-like speech rhythm and varied intonation",
)

# --- TTS Generation Parameters ---
# Qwen recommended: temperature=0.6~0.7, top_p=0.8~0.95
# WARNING: Do NOT use temperature=0 (greedy) - causes infinite repetitions
TTS_TEMPERATURE = float(os.getenv("TTS_TEMPERATURE", "0.7"))  # Increased slightly for naturalness
TTS_TOP_P = float(os.getenv("TTS_TOP_P", "0.8"))  # Nucleus sampling (Qwen recommended)
TTS_REPETITION_PENALTY = float(
    os.getenv("TTS_REPETITION_PENALTY", "1.0")
)  # Lowered from 1.2 to 1.0 (speed + reduce hallucination)
TTS_MAX_NEW_TOKENS = int(
    os.getenv("TTS_MAX_NEW_TOKENS", "1024")
)  # Reduced from 2048: shorts scripts are short, 1024 is sufficient and faster

# --- TTS Quality Validation & Retry ---
TTS_MIN_DURATION_SEC = float(os.getenv("TTS_MIN_DURATION_SEC", "1.0"))  # Min TTS length (sec)
TTS_MIN_SPEAKABLE_CHARS = int(os.getenv("TTS_MIN_SPEAKABLE_CHARS", "2"))  # Min word chars for TTS
TTS_MAX_RETRIES = int(os.getenv("TTS_MAX_RETRIES", "2"))  # Retry count on quality failure

# --- TTS Performance ---
TTS_TIMEOUT_SECONDS = int(os.getenv("TTS_TIMEOUT_SECONDS", "120"))
TTS_CACHE_DIR = PROMPT_CACHE_DIR / "tts"
TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# --- MusicGen (AI BGM) ---
MUSICGEN_DEFAULT_DURATION = float(os.getenv("MUSICGEN_DEFAULT_DURATION", "30.0"))
MUSICGEN_MAX_DURATION = float(os.getenv("MUSICGEN_MAX_DURATION", "30.0"))
MUSICGEN_SAMPLE_RATE = int(os.getenv("MUSICGEN_SAMPLE_RATE", "32000"))
MUSICGEN_CACHE_DIR = PROMPT_CACHE_DIR / "music"
MUSICGEN_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# --- Storyboard Options (SSOT) ---
STORYBOARD_LANGUAGES = [
    {"value": "Korean", "label": "한국어"},
    {"value": "English", "label": "English"},
    {"value": "Japanese", "label": "日本語"},
]
SHORTS_DURATIONS = [15, 30, 45, 60]

# --- Script Length Rules (SSOT for scriptwriter.j2 + creative_qc.py) ---
SCRIPT_LENGTH_KOREAN = (5, 35)  # (min_chars, max_chars)
SCRIPT_LENGTH_OTHER = (3, 18)  # (min_words, max_words)
SCENE_DURATION_RANGE = (2.0, 3.5)  # (min_seconds, max_seconds) per scene
SCENE_DEFAULT_DURATION = 3.0  # fallback duration for invalid scenes (revise node)
REVIEW_SCRIPT_MAX_CHARS_OTHER = 70  # char-level review threshold for non-Korean (~max_words * avg_chars)

# --- Reading Speed (SSOT for duration estimation + Frontend display) ---
READING_SPEED: dict[str, dict] = {
    "Korean": {"cps": 4.0, "unit": "chars"},
    "Japanese": {"cps": 5.0, "unit": "chars"},
    "English": {"wps": 2.5, "unit": "words"},
}
READING_DURATION_PADDING = 0.5  # seconds (자연스러운 호흡 간격)
SCENE_DURATION_MAX = 10.0  # absolute safety cap per scene
DURATION_DEFICIT_THRESHOLD = 0.85  # 총 duration이 target의 이 비율 미만이면 부족으로 판정

# --- Pipeline & Integration Constants (extracted to config_pipelines.py) ---
from config_pipelines import *  # noqa: E402, F401, F403

# --- Upload Limits ---
MAX_IMAGE_UPLOAD_BYTES = int(os.getenv("MAX_IMAGE_UPLOAD_BYTES", str(10 * 1024 * 1024)))  # 10MB
# Max size for base64-decoded images (separate from file upload limit)
MAX_BASE64_IMAGE_SIZE_MB = int(os.getenv("MAX_BASE64_IMAGE_SIZE_MB", "20"))
MAX_BASE64_IMAGE_SIZE_BYTES = MAX_BASE64_IMAGE_SIZE_MB * 1024 * 1024

# --- SSRF Prevention ---
# Allowed hosts for image loading via HTTP (load_image_bytes).
# localhost / 127.0.0.1 are needed for SD WebUI and MinIO in dev.
# Add production hostnames via env: ALLOWED_IMAGE_HOSTS=host1,host2
_default_image_hosts = "localhost,127.0.0.1"
ALLOWED_IMAGE_HOSTS: set[str] = {
    h.strip() for h in os.getenv("ALLOWED_IMAGE_HOSTS", _default_image_hosts).split(",") if h.strip()
}

# --- Storage Credential Minimum Length ---
MINIO_SECRET_KEY_MIN_LENGTH = 12


def validate_storage_config() -> None:
    """Validate storage credentials at startup (S3 mode only).

    Raises ValueError if STORAGE_MODE is 's3' and credentials are empty.
    Logs a warning if the secret key is shorter than the minimum length.
    """
    if STORAGE_MODE != "s3":
        return

    if not MINIO_ACCESS_KEY or not MINIO_SECRET_KEY:
        raise ValueError("MINIO_ACCESS_KEY 및 MINIO_SECRET_KEY 환경 변수가 필요합니다. backend/.env 파일에 설정하세요.")

    if len(MINIO_SECRET_KEY) < MINIO_SECRET_KEY_MIN_LENGTH:
        logger.warning(
            "MINIO_SECRET_KEY가 %d자 미만입니다. 보안을 위해 %d자 이상을 권장합니다.",
            MINIO_SECRET_KEY_MIN_LENGTH,
            MINIO_SECRET_KEY_MIN_LENGTH,
        )
