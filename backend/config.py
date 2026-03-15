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
# Gemini Fallback Model — PROHIBITED_CONTENT 차단 시 자동 폴백 (2.0 Flash는 과도한 필터 없음)
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.0-flash")
# Gemini Vision 태그 평가 타임아웃 (초) — evaluate_tags_with_gemini
GEMINI_VISION_EVAL_TIMEOUT_S = int(os.getenv("GEMINI_VISION_EVAL_TIMEOUT_S", "5"))
GEMINI_EVAL_BATCH_CONCURRENCY = int(os.getenv("GEMINI_EVAL_BATCH_CONCURRENCY", "3"))

# 공통 Safety Settings — 모든 Gemini 호출에서 재사용 (config.py SSOT)
_BLOCK_NONE = genai.types.HarmBlockThreshold.BLOCK_NONE
GEMINI_SAFETY_SETTINGS: list[genai.types.SafetySetting] = [
    genai.types.SafetySetting(category=genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=_BLOCK_NONE),
    genai.types.SafetySetting(category=genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=_BLOCK_NONE),
    genai.types.SafetySetting(category=genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=_BLOCK_NONE),
    genai.types.SafetySetting(category=genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=_BLOCK_NONE),
    genai.types.SafetySetting(category=genai.types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY, threshold=_BLOCK_NONE),
]

template_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

SD_BASE_URL = os.getenv("SD_BASE_URL", "http://127.0.0.1:7860")
if SD_BASE_URL == "http://127.0.0.1:7860":
    logger.info("Using default SD_BASE_URL: %s", SD_BASE_URL)

# --- Audio Server (TTS + MusicGen sidecar) ---
AUDIO_SERVER_URL = os.getenv("AUDIO_SERVER_URL", "http://127.0.0.1:8001")
AUDIO_TIMEOUT_SECONDS = float(os.getenv("AUDIO_TIMEOUT_SECONDS", "180"))
MUSIC_TIMEOUT_SECONDS = float(os.getenv("MUSIC_TIMEOUT_SECONDS", "600"))  # 10min for MusicGen
AUDIO_SERVER_TTS_CACHE_DIR = pathlib.Path(
    os.getenv("AUDIO_SERVER_TTS_CACHE_DIR", str(pathlib.Path.home() / ".cache" / "audio-server" / "tts"))
)

SD_TXT2IMG_URL = f"{SD_BASE_URL}/sdapi/v1/txt2img"
SD_MODELS_URL = f"{SD_BASE_URL}/sdapi/v1/sd-models"
SD_OPTIONS_URL = f"{SD_BASE_URL}/sdapi/v1/options"
SD_LORAS_URL = f"{SD_BASE_URL}/sdapi/v1/loras"
SD_TIMEOUT_SECONDS = float(os.getenv("SD_TIMEOUT_SECONDS", "600"))
SD_BATCH_CONCURRENCY = int(os.getenv("SD_BATCH_CONCURRENCY", "3"))

# --- Image Generation Defaults ---
# NoobAI-XL V-Pred 1.0: Euler only, CFG 4~5, 832x1216 (2:3, ~1M pixels)
SD_DEFAULT_WIDTH = int(os.getenv("SD_DEFAULT_WIDTH", "832"))
SD_DEFAULT_HEIGHT = int(os.getenv("SD_DEFAULT_HEIGHT", "1216"))
SD_DEFAULT_STEPS = int(os.getenv("SD_DEFAULT_STEPS", "28"))
SD_DEFAULT_CFG_SCALE = float(os.getenv("SD_DEFAULT_CFG_SCALE", "4.5"))
SD_DEFAULT_SAMPLER = os.getenv("SD_DEFAULT_SAMPLER", "Euler")
SD_DEFAULT_CLIP_SKIP = int(os.getenv("SD_DEFAULT_CLIP_SKIP", "2"))
# V-Pred CFG Rescale (prevents grey output at higher CFG values)
SD_CFG_RESCALE = float(os.getenv("SD_CFG_RESCALE", "0.2"))

# --- LoRA Weight Cap ---
# Maximum weight for style LoRAs (applied to both character and narrator scenes)
STYLE_LORA_WEIGHT_CAP = float(os.getenv("STYLE_LORA_WEIGHT_CAP", "0.76"))


def cap_style_lora_weight(weight: float, lora_type: str | None) -> float:
    """Cap weight for style/detail LoRAs. Returns weight unchanged for other types."""
    if lora_type in ("style", "detail"):
        return round(min(weight, STYLE_LORA_WEIGHT_CAP), 2)
    return weight


# --- Forge Sampler/Scheduler Split ---
_KNOWN_SCHEDULERS = {"karras", "exponential", "polyexponential"}


def split_sampler_scheduler(sampler_name: str) -> tuple[str, str | None]:
    """Split A1111-style sampler into Forge sampler + scheduler.

    Forge separates sampler and scheduler into distinct API fields.
    e.g. "DPM++ 2M Karras" → ("DPM++ 2M", "karras")
         "Euler a"          → ("Euler a", None)
    """
    parts = sampler_name.rsplit(" ", 1)
    if len(parts) == 2 and parts[1].lower() in _KNOWN_SCHEDULERS:
        return parts[0], parts[1]  # Preserve original case (Forge expects "Karras" not "karras")
    return sampler_name, None


def apply_sampler_to_payload(payload: dict, sampler_name: str) -> None:
    """Set sampler_name, scheduler, and CFG Rescale in payload for Forge compatibility."""
    sampler, scheduler = split_sampler_scheduler(sampler_name)
    payload["sampler_name"] = sampler
    if scheduler:
        payload["scheduler"] = scheduler
    # V-Pred CFG Rescale (prevents grey output)
    if SD_CFG_RESCALE > 0:
        payload.setdefault("extra_generation_params", {})["CFG Rescale φ"] = SD_CFG_RESCALE


# --- SD API Timeouts ---
SD_API_TIMEOUT = float(os.getenv("SD_API_TIMEOUT", "10"))
SD_MODEL_SWITCH_TIMEOUT = float(os.getenv("SD_MODEL_SWITCH_TIMEOUT", "120"))

# --- ControlNet Timeouts ---
CONTROLNET_API_TIMEOUT = float(os.getenv("CONTROLNET_API_TIMEOUT", "10"))
CONTROLNET_GENERATE_TIMEOUT = float(os.getenv("CONTROLNET_GENERATE_TIMEOUT", "180"))
CONTROLNET_DETECT_TIMEOUT = float(os.getenv("CONTROLNET_DETECT_TIMEOUT", "60"))
# Default sampler for ControlNet-only generation (not using StyleProfile)
CONTROLNET_DEFAULT_SAMPLER = os.getenv("CONTROLNET_DEFAULT_SAMPLER", "Euler")

# --- Character Reference Generation ---
SD_REFERENCE_STEPS = int(os.getenv("SD_REFERENCE_STEPS", "28"))
SD_REFERENCE_CFG_SCALE = float(os.getenv("SD_REFERENCE_CFG_SCALE", "4.5"))
SD_REFERENCE_HR_UPSCALER = os.getenv("SD_REFERENCE_HR_UPSCALER", "R-ESRGAN 4x+ Anime6B")
SD_REFERENCE_DENOISING = float(os.getenv("SD_REFERENCE_DENOISING", "0.35"))
# ControlNet pose for reference images (empty = disabled, upper_body framing only)
SD_REFERENCE_CONTROLNET_POSE = os.getenv("SD_REFERENCE_CONTROLNET_POSE", "")
SD_REFERENCE_CONTROLNET_WEIGHT = float(os.getenv("SD_REFERENCE_CONTROLNET_WEIGHT", "0.8"))
SD_REFERENCE_CONTROLNET_MODE = os.getenv("SD_REFERENCE_CONTROLNET_MODE", "ControlNet is more important")
# Number of candidate images to generate for character preview selection
SD_REFERENCE_NUM_CANDIDATES = int(os.getenv("SD_REFERENCE_NUM_CANDIDATES", "3"))
# Character LoRA weight multiplier for reference images (identity hint only)
# 0.4: balanced between character identity and pose freedom (reviewed 2026-02)
REFERENCE_LORA_SCALE = float(os.getenv("REFERENCE_LORA_SCALE", "0.4"))
# Style LoRA weight multiplier for reference images
# SDXL(NoobAI-XL): 씬과 동일한 스타일 보장을 위해 1.0 (full weight)
REFERENCE_STYLE_LORA_SCALE = float(os.getenv("REFERENCE_STYLE_LORA_SCALE", "1.0"))
# Character LoRA weight multiplier for scene images
# 0.45: prevents LoRA from overriding clothing color tags while preserving face identity
# Without scaling, LoRA at full weight (0.7) dominates clothing — text tags ignored
SCENE_CHARACTER_LORA_SCALE = float(os.getenv("SCENE_CHARACTER_LORA_SCALE", "0.45"))

# --- Multi-Character Scene ---
MULTI_CHAR_NEGATIVE_EXTRA = os.getenv("MULTI_CHAR_NEGATIVE_EXTRA", "solo, fused_body, merged_body")
MULTI_CHAR_MAX_TOTAL_LORA_WEIGHT = float(os.getenv("MULTI_CHAR_MAX_TOTAL_LORA_WEIGHT", "1.5"))

# --- Base Model ---
# SSOT for SD base model identifiers. All API inputs are normalized to these values.
SUPPORTED_BASE_MODELS: set[str] = {"SD1.5", "SDXL", "FLUX"}
# Normalization map: common variants → canonical value
BASE_MODEL_ALIASES: dict[str, str] = {
    "sd1.5": "SD1.5",
    "sd 1.5": "SD1.5",
    "sd15": "SD1.5",
    "sd1_5": "SD1.5",
    "sdxl": "SDXL",
    "sd xl": "SDXL",
    "flux": "FLUX",
}


def normalize_base_model(value: str | None) -> str | None:
    """Normalize base_model to canonical form. Returns None if input is None."""
    if value is None:
        return None
    canonical = BASE_MODEL_ALIASES.get(value.strip().lower())
    if canonical:
        return canonical
    # Already canonical
    if value in SUPPORTED_BASE_MODELS:
        return value
    return value  # unknown value — pass through, don't block


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

# --- Match Rate: Group-based Tag Routing (Phase 33) ---
# DB tags.group_name을 기반으로 각 태그의 평가 방법을 결정한다.
# WD14_UNMATCHABLE_TAGS (하드코딩) → 그룹 기반 라우팅으로 대체.

# Tag groups where WD14 can reliably detect presence/absence.
# 시각적 특징 — 로컬 WD14 모델로 무료/즉시 평가.
WD14_DETECTABLE_GROUPS: frozenset[str] = frozenset(
    {
        "subject",  # 1girl, solo — 0.9+ confidence
        "hair_color",  # black_hair, blonde_hair
        "hair_length",  # long_hair, short_hair
        "hair_style",  # ponytail, twintails
        "hair_accessory",  # hairclip, hairband
        "eye_color",  # blue_eyes, red_eyes
        "eye_detail",  # heterochromia, slit_pupils
        "skin_color",  # dark_skin, pale_skin
        # clothing 계열
        "clothing",  # 레거시 미분류 (935개)
        "clothing_top",  # shirt, jacket
        "clothing_bottom",  # skirt, pants
        "clothing_outfit",  # dress, uniform
        "clothing_detail",  # long_sleeves, frills
        "legwear",  # thighhighs, stockings
        "footwear",  # boots, sneakers
        "accessory",  # glasses, hat, earrings
        "expression",  # smile, open_mouth
        "gaze",  # looking_at_viewer, closed_eyes
        "pose",  # standing, sitting
        "gesture",  # pointing, waving
        # action 계열
        "action",  # 레거시 미분류 (229개)
        "action_body",  # walking, running
        "action_hand",  # holding, grabbing
        "action_daily",  # reading, eating
        "body_feature",  # cat_ears, wings
        "appearance",  # freckles, makeup
        "body_type",  # slim, muscular
        "identity",  # 캐릭터 정체성 (hair/eye 기반)
    }
)

# Tag groups evaluated by Gemini Vision (non-visual / contextual).
# WD14가 감지 못하는 구도, 조명, 분위기, 환경 태그를 Gemini로 평가.
GEMINI_DETECTABLE_GROUPS: frozenset[str] = frozenset(
    {
        "camera",  # cowboy_shot, close-up, from_above
        "lighting",  # sidelighting, soft_shadow
        "mood",  # peaceful, romantic, melancholy
        "environment",  # 환경 전반 (224개)
        "location_outdoor",  # park, street, beach
        "location_indoor",  # indoors
        "location_indoor_specific",  # classroom, library, cafe
        "location_indoor_general",  # indoors 일반
        "time_weather",  # rain, sunset, night_sky
        "time_of_day",  # morning, night
        "weather",  # rain, snow, cloudy
    }
)

# Tag groups excluded from match rate calculation entirely.
# 평가 불필요하거나 감지 불가능한 태그 — 분모에서 제외.
SKIPPABLE_GROUPS: frozenset[str] = frozenset(
    {
        "quality",  # masterpiece, best_quality
        "skip",  # 명시적 스킵 태그
        "style",  # flat_color, cel_shading (렌더링 스타일)
        "danbooru_validated",  # 메타 태그
        "background_type",  # simple_background, white_background
        "particle",  # 파티클 효과 (감지 어려움)
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

# --- ADetailer (face + hand inpainting post-process) ---
ADETAILER_ENABLED: bool = True
ADETAILER_FACE_MODEL: str = "face_yolov8n.pt"  # default: fast model
ADETAILER_HAND_MODEL: str = "hand_yolov8n.pt"  # hand fix model
ADETAILER_HAND_ENABLED: bool = True  # Enable hand inpainting (2nd unit)
ADETAILER_DENOISING_STRENGTH: float = 0.4  # 0.3–0.5 safe range
ADETAILER_HAND_DENOISING_STRENGTH: float = 0.35  # Slightly lower for hands (preserve pose)
ADETAILER_HIGH_ACCURACY_PROFILE_IDS: set[int] = {2}  # face_yolov8s.pt (Realistic)

# --- IP-Adapter Reference Auto-Crop ---
IP_ADAPTER_REFERENCE_AUTO_CROP: bool = True  # Auto-crop fullbody → upper body
IP_ADAPTER_REFERENCE_CROP_RATIO: float = 0.4  # Top 40% of image (head + shoulders)

# --- Prompt Composition Constants (extracted to config_prompt.py) ---
from config_prompt import *  # noqa: E402, F401, F403

# --- Reference Image Generation Defaults ---
# Default prompts for generating IP-Adapter reference images
# Used when creating new characters without custom reference prompts
DEFAULT_REFERENCE_BASE_PROMPT = ", ".join(
    [
        "masterpiece",
        "best_quality",
        "ultra-detailed",
        "solo",
        "upper_body",
        "looking_at_viewer",
        "(simple_background:1.3)",
        "(white_background:1.3)",
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
        # --- 배경 억제 (깨끗한 배경 유지, 렌더링 스타일은 억제하지 않음) ---
        "busy_background",
        "detailed_background",
        "(dark_background:1.3)",
        "(black_background:1.3)",
        "night",
        "night_sky",
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
DEFAULT_SCENE_NEGATIVE_PROMPT = "lowres, bad_anatomy, bad_hands, text, error, missing_fingers, extra_digit, fewer_digits, cropped, worst_quality, low_quality, jpeg_artifacts, signature, watermark, username, blurry, multiple_views, split_screen, comic_panel, multiple_panels, collage, border, frame"

# Extra negative tags appended for Narrator scenes (no_humans) to suppress character generation
NARRATOR_NEGATIVE_PROMPT_EXTRA = "1girl, 1boy, 2girls, 2boys, multiple_girls, multiple_boys, person, human, male, female, solo, couple, face, portrait, upper_body, cowboy_shot"

# Stage Workflow status values (Phase 18)
STAGE_STATUS_PENDING = "pending"
STAGE_STATUS_STAGING = "staging"
STAGE_STATUS_STAGED = "staged"
STAGE_STATUS_FAILED = "failed"

# Background quality overrides per StyleProfile ID.
# StyleProfile.default_positive is optimized for character scenes;
# background generation uses different atmospheric quality tags.
# Keyed by StyleProfile.id.
BG_QUALITY_OVERRIDES: dict[int, str] = {
    2: "RAW photo, soft ambient lighting, muted tones, shallow depth of field, natural light, 35mm film, high quality",  # Realistic
}

# Reference AdaIN — environment atmosphere transfer (replaces Canny for BG pinning)
# Transfers color statistics (mean/variance) only, no spatial structure
REFERENCE_ADAIN_WEIGHT = float(os.getenv("REFERENCE_ADAIN_WEIGHT", "0.35"))
REFERENCE_ADAIN_WEIGHT_INDOOR = float(os.getenv("REFERENCE_ADAIN_WEIGHT_INDOOR", "0.40"))
REFERENCE_ADAIN_WEIGHT_OUTDOOR = float(os.getenv("REFERENCE_ADAIN_WEIGHT_OUTDOOR", "0.25"))
REFERENCE_ADAIN_GUIDANCE_END = float(os.getenv("REFERENCE_ADAIN_GUIDANCE_END", "0.5"))

# Default pose/gaze/expression/mood for ControlNet when Gemini omits context_tags
DEFAULT_POSE_TAG = "standing"
DEFAULT_GAZE_TAG = "looking_at_viewer"
DEFAULT_EXPRESSION_TAG = "smile"
DEFAULT_MOOD_TAG = "neutral"

# --- Gemini Imagen Cost (USD per request) ---
GEMINI_IMAGE_EDIT_COST_USD = float(os.getenv("GEMINI_IMAGE_EDIT_COST_USD", "0.0401"))
GEMINI_IMAGE_VISION_COST_USD = float(os.getenv("GEMINI_IMAGE_VISION_COST_USD", "0.0003"))
GEMINI_IMAGE_EDIT_TOTAL_COST_USD = float(os.getenv("GEMINI_IMAGE_EDIT_TOTAL_COST_USD", "0.0404"))

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
MIN_IP_ADAPTER_WEIGHT_NO_LORA = 0.5  # LoRA 없는 캐릭터의 최소 IP-Adapter weight
DEFAULT_MULTI_GEN_ENABLED = False

# --- IP-Adapter Defaults ---
# Default IP-Adapter settings (per-character overrides stored in DB)
# weight=0.50: V2 상향 (기존 0.35, 업계 권장 0.5~0.7)
DEFAULT_CHARACTER_PRESET = {
    "weight": 0.50,
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
TTS_VOICE_CONSISTENCY_MODE = os.getenv("TTS_VOICE_CONSISTENCY_MODE", "false").lower() == "true"

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
    "with natural, human-like speech rhythm, varied intonation, and a slightly fast conversational pace",
)

# --- TTS Generation Parameters ---
# Qwen recommended: temperature=0.6~0.7, top_p=0.8~0.95
# WARNING: Do NOT use temperature=0 (greedy) - causes infinite repetitions
TTS_TEMPERATURE = float(os.getenv("TTS_TEMPERATURE", "0.7"))  # Increased slightly for naturalness
TTS_TOP_P = float(os.getenv("TTS_TOP_P", "0.8"))  # Nucleus sampling (Qwen recommended)
TTS_REPETITION_PENALTY = float(
    os.getenv("TTS_REPETITION_PENALTY", "1.05")
)  # Qwen3-TTS default: 1.05 (stabilize autoregressive generation)
TTS_MAX_NEW_TOKENS = int(
    os.getenv("TTS_MAX_NEW_TOKENS", "1024")
)  # Deprecated: Audio Server 기본값용. Backend는 TTS_MAX_NEW_TOKENS_BASE/PER_CHAR/CAP 사용
TTS_MAX_NEW_TOKENS_BASE = int(os.getenv("TTS_MAX_NEW_TOKENS_BASE", "1024"))
TTS_MAX_NEW_TOKENS_PER_CHAR = int(os.getenv("TTS_MAX_NEW_TOKENS_PER_CHAR", "30"))
TTS_MAX_NEW_TOKENS_CAP = int(os.getenv("TTS_MAX_NEW_TOKENS_CAP", "2048"))

# --- TTS Quality Validation & Retry ---
TTS_MIN_DURATION_SEC = float(os.getenv("TTS_MIN_DURATION_SEC", "1.0"))  # Min TTS length (sec)
TTS_MIN_SPEAKABLE_CHARS = int(os.getenv("TTS_MIN_SPEAKABLE_CHARS", "2"))  # Min word chars for TTS
TTS_MAX_RETRIES = int(os.getenv("TTS_MAX_RETRIES", "2"))  # Retry count on quality failure
TTS_DEFAULT_SEED = int(os.getenv("TTS_DEFAULT_SEED", "42"))  # Fallback seed when preset has no seed

TTS_PREVIEW_BATCH_CONCURRENCY = int(os.getenv("TTS_PREVIEW_BATCH_CONCURRENCY", "3"))
TTS_PREBUILD_CONCURRENCY = int(os.getenv("TTS_PREBUILD_CONCURRENCY", "3"))  # Autopilot prebuild 동시성
MAX_PREVIEW_IMAGE_BYTES = int(os.getenv("MAX_PREVIEW_IMAGE_BYTES", str(10 * 1024 * 1024)))  # 10MB

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
DURATION_OVERFLOW_THRESHOLD = 1.3  # 총 duration이 target의 이 비율 초과이면 오버로 판정

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
