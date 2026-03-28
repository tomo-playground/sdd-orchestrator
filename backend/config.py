"""Configuration and global objects for Shorts Producer Backend.

Centralizes all configuration, constants, and shared objects.
"""

from __future__ import annotations

import logging
import os
import pathlib

from dotenv import load_dotenv
from google import genai

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

_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

_handlers: list[logging.Handler] = [logging.StreamHandler()]
if LOG_TO_FILE:
    _log_path = pathlib.Path(LOG_FILE)
    _log_path.parent.mkdir(parents=True, exist_ok=True)
    _handlers.append(logging.FileHandler(_log_path, encoding="utf-8"))

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=_LOG_FORMAT,
    datefmt=_LOG_DATEFMT,
    handlers=_handlers,
)

logger = logging.getLogger("backend")
# propagate=True (default): root logger's handlers (StreamHandler + FileHandler) handle all output.
# Do NOT add a separate FileHandler here — it causes duplicate log entries in the log file.


def _make_file_logger(name: str, filename: str) -> logging.Logger:
    """Create a hierarchical logger with its own FileHandler.

    Messages propagate to root (→ backend.log + console) AND go to their own file.
    """
    child = logging.getLogger(name)
    if LOG_TO_FILE:
        path = pathlib.Path("logs") / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(path, encoding="utf-8")
        fh.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATEFMT))
        child.addHandler(fh)
    return child


pipeline_logger = _make_file_logger("backend.pipeline", "pipeline.log")
gemini_logger = _make_file_logger("backend.gemini", "gemini.log")

# --- Database ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.warning("DATABASE_URL is not set. Database functionality will fail.")

# --- DB Connection Pool ---
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))
DB_POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "1").lower() not in {"0", "false", "no"}

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
# Used for prompt rewriting, translation, validation, and vision analysis
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
# Gemini Classifier Model — 태그 분류 전용 (lightweight, 항상 Flash 사용)
GEMINI_CLASSIFIER_MODEL = os.getenv("GEMINI_CLASSIFIER_MODEL", "gemini-2.5-flash")
GEMINI_CLASSIFIER_TIMEOUT_MS = int(os.getenv("GEMINI_CLASSIFIER_TIMEOUT_MS", "30000"))
# Gemini Fallback Model — PROHIBITED_CONTENT 차단 시 자동 폴백 (2.0 Flash는 과도한 필터 없음)
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.0-flash")
# Gemini Vision 태그 평가 타임아웃 (초) — evaluate_tags_with_gemini
GEMINI_VISION_EVAL_TIMEOUT_S = int(os.getenv("GEMINI_VISION_EVAL_TIMEOUT_S", "5"))
GEMINI_EVAL_BATCH_CONCURRENCY = int(os.getenv("GEMINI_EVAL_BATCH_CONCURRENCY", "3"))
# Gemini 글로벌 timeout (ms) — 모든 generate 호출에 적용
GEMINI_TIMEOUT_MS = int(os.getenv("GEMINI_TIMEOUT_MS", "120000"))
# Gemini 동시 호출 제한 — generate_parallel Semaphore 상한
GEMINI_MAX_CONCURRENT = int(os.getenv("GEMINI_MAX_CONCURRENT", "5"))

# 공통 Safety Settings — 모든 Gemini 호출에서 재사용 (config.py SSOT)
_BLOCK_NONE = genai.types.HarmBlockThreshold.BLOCK_NONE
GEMINI_SAFETY_SETTINGS: list[genai.types.SafetySetting] = [
    genai.types.SafetySetting(category=genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=_BLOCK_NONE),
    genai.types.SafetySetting(category=genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=_BLOCK_NONE),
    genai.types.SafetySetting(category=genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=_BLOCK_NONE),
    genai.types.SafetySetting(category=genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=_BLOCK_NONE),
    genai.types.SafetySetting(category=genai.types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY, threshold=_BLOCK_NONE),
]


SD_BASE_URL = os.getenv("SD_BASE_URL", "http://127.0.0.1:7860")

# --- ComfyUI ---
COMFYUI_BASE_URL = os.getenv("COMFYUI_BASE_URL", "http://127.0.0.1:8188")
logger.info("ComfyUI endpoint: %s", COMFYUI_BASE_URL)
COMFYUI_NETWORK_TIMEOUT = float(os.getenv("COMFYUI_NETWORK_TIMEOUT", "10"))
COMFYUI_EXECUTION_TIMEOUT = float(os.getenv("COMFYUI_EXECUTION_TIMEOUT", "180"))
COMFYUI_QUEUE_TIMEOUT = float(os.getenv("COMFYUI_QUEUE_TIMEOUT", "300"))

# --- Audio Server (Qwen3-TTS + MusicGen 통합 사이드카) ---
AUDIO_SERVER_URL = os.getenv("AUDIO_SERVER_URL", "http://127.0.0.1:8001")
AUDIO_TIMEOUT_SECONDS = float(os.getenv("AUDIO_TIMEOUT_SECONDS", "180"))
MUSIC_TIMEOUT_SECONDS = float(os.getenv("MUSIC_TIMEOUT_SECONDS", "600"))  # 10min for MusicGen
VOICE_REF_SAMPLE_TEXT = "안녕하세요. 오늘 하루도 좋은 하루 되시길 바랍니다. 함께 이야기를 나눠볼까요?"
AUDIO_SERVER_TTS_CACHE_DIR = pathlib.Path(
    os.getenv("AUDIO_SERVER_TTS_CACHE_DIR", str(pathlib.Path.home() / ".cache" / "audio-server" / "tts"))
)

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

# --- Hi-Res Fix Defaults ---
SD_HI_RES_SCALE = float(os.getenv("SD_HI_RES_SCALE", "1.5"))
SD_HI_RES_UPSCALER = os.getenv("SD_HI_RES_UPSCALER", "R-ESRGAN 4x+ Anime6B")
SD_HI_RES_SECOND_PASS_STEPS = int(os.getenv("SD_HI_RES_SECOND_PASS_STEPS", "10"))
SD_HI_RES_DENOISING_STRENGTH = float(os.getenv("SD_HI_RES_DENOISING_STRENGTH", "0.35"))

# --- Sampler Options (SSOT for Frontend) ---
SD_SAMPLERS: list[str] = [
    "Euler",
    "Euler a",
    "DPM++ 2M",
    "DPM++ 2M Karras",
    "DPM++ SDE Karras",
    "DDIM",
]

# --- TTS Engine ---
SUPPORTED_TTS_ENGINES: list[str] = ["qwen"]
DEFAULT_TTS_ENGINE = os.getenv("DEFAULT_TTS_ENGINE", "qwen")

# --- LoRA Weight Cap ---
# Maximum weight for style LoRAs (applied to both character and narrator scenes)
STYLE_LORA_WEIGHT_CAP = float(os.getenv("STYLE_LORA_WEIGHT_CAP", "0.76"))


def cap_style_lora_weight(weight: float, lora_type: str | None) -> float:
    """Cap weight for style/detail LoRAs. Returns weight unchanged for other types."""
    if lora_type in ("style", "detail"):
        return round(min(weight, STYLE_LORA_WEIGHT_CAP), 2)
    return weight


# --- Sampler/Scheduler Split ---
_KNOWN_SCHEDULERS = {"karras", "exponential", "polyexponential"}


def split_sampler_scheduler(sampler_name: str) -> tuple[str, str | None]:
    """Split A1111-style sampler into sampler + scheduler.

    e.g. "DPM++ 2M Karras" → ("DPM++ 2M", "karras")
         "Euler a"          → ("Euler a", None)
    """
    parts = sampler_name.rsplit(" ", 1)
    if len(parts) == 2 and parts[1].lower() in _KNOWN_SCHEDULERS:
        return parts[0], parts[1]
    return sampler_name, None


def apply_sampler_to_payload(payload: dict, sampler_name: str) -> None:
    """Set sampler_name, scheduler, and CFG Rescale in payload."""
    sampler, scheduler = split_sampler_scheduler(sampler_name)
    payload["sampler_name"] = sampler
    if scheduler:
        payload["scheduler"] = scheduler
    # V-Pred CFG Rescale (prevents grey output)
    if SD_CFG_RESCALE > 0:
        payload.setdefault("extra_generation_params", {})["CFG Rescale φ"] = SD_CFG_RESCALE


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
CONTROLNET_2P_STRENGTH = float(os.getenv("CONTROLNET_2P_STRENGTH", "0.7"))
CONTROLNET_2P_DEFAULT_POSE = os.getenv("CONTROLNET_2P_DEFAULT_POSE", "standing_side_by_side")

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
if CHECKPOINT_GC_RETENTION_DAYS < 1:
    raise ValueError("CHECKPOINT_GC_RETENTION_DAYS must be >= 1")

# --- Build Dir GC ---
BUILD_DIR_GC_RETENTION_HOURS = int(os.getenv("BUILD_DIR_GC_RETENTION_HOURS", "24"))
if BUILD_DIR_GC_RETENTION_HOURS < 1:
    raise ValueError("BUILD_DIR_GC_RETENTION_HOURS must be >= 1")

# --- Font & LoRA Defaults ---
DEFAULT_SCENE_TEXT_FONT = os.getenv("DEFAULT_SCENE_TEXT_FONT", "온글잎 박다현체.ttf")
DEFAULT_LORA_WEIGHT = float(os.getenv("DEFAULT_LORA_WEIGHT", "0.7"))

# --- Structure & Language SSOT (Sprint A: Enum ID 정규화) ---
from dataclasses import dataclass  # noqa: E402


@dataclass(frozen=True)
class StructureMeta:
    """구조 메타데이터 (인메모리 상수)."""

    id: str
    label: str
    label_ko: str
    requires_two_characters: bool
    default_tone: str


STRUCTURE_METADATA: tuple[StructureMeta, ...] = (
    StructureMeta(
        id="monologue", label="Monologue", label_ko="독백", requires_two_characters=False, default_tone="intimate"
    ),
    StructureMeta(
        id="dialogue", label="Dialogue", label_ko="대화형", requires_two_characters=True, default_tone="dynamic"
    ),
    StructureMeta(
        id="narrated_dialogue",
        label="Narrated Dialogue",
        label_ko="내레이션 대화",
        requires_two_characters=True,
        default_tone="intimate",
    ),
)


@dataclass(frozen=True)
class ToneMeta:
    """톤 메타데이터 (인메모리 상수)."""

    id: str
    label: str
    label_ko: str


TONE_METADATA: tuple[ToneMeta, ...] = (
    ToneMeta(id="intimate", label="Intimate", label_ko="담담"),
    ToneMeta(id="emotional", label="Emotional", label_ko="감정적"),
    ToneMeta(id="dynamic", label="Dynamic", label_ko="역동적"),
    ToneMeta(id="humorous", label="Humorous", label_ko="유머"),
    ToneMeta(id="suspense", label="Suspense", label_ko="서스펜스"),
)

TONE_IDS: frozenset[str] = frozenset(t.id for t in TONE_METADATA)
DEFAULT_TONE = "intimate"
TONE_HINTS: dict[str, str] = {
    "intimate": "Write in a calm, introspective tone. Focus on inner thoughts.",
    "emotional": "Write with deep emotion. Include vulnerable moments and heartfelt expressions.",
    "dynamic": "Write with energy and tension. Use short, punchy dialogue.",
    "humorous": "Write with wit and humor. Include comedic timing and light moments.",
    "suspense": "Write with tension and mystery. Build suspense gradually.",
}

STRUCTURE_IDS: frozenset[str] = frozenset(s.id for s in STRUCTURE_METADATA)
MULTI_CHAR_STRUCTURES: frozenset[str] = frozenset(s.id for s in STRUCTURE_METADATA if s.requires_two_characters)
STRUCTURE_ID_TO_LABEL: dict[str, str] = {s.id: s.label for s in STRUCTURE_METADATA}
STRUCTURE_LABEL_TO_ID: dict[str, str] = {s.label: s.id for s in STRUCTURE_METADATA}
STRUCTURE_HINTS: dict[str, str] = {
    "monologue": "혼자 이야기하는 독백 형태",
    "dialogue": "두 캐릭터가 대화하는 형태",
    "narrated_dialogue": "나레이션과 대화가 섞인 형태",
}


@dataclass(frozen=True)
class LanguageMeta:
    """언어 메타데이터."""

    id: str
    label: str


LANGUAGE_METADATA: tuple[LanguageMeta, ...] = (
    LanguageMeta(id="korean", label="한국어"),
    LanguageMeta(id="english", label="English"),
    LanguageMeta(id="japanese", label="日本語"),
)

LANGUAGE_IDS: frozenset[str] = frozenset(lang.id for lang in LANGUAGE_METADATA)

DEFAULT_STRUCTURE = "monologue"
DEFAULT_LANGUAGE = "korean"
DEFAULT_SPEAKER = "narrator"  # Default speaker for scenes
DEFAULT_PLATFORM = "youtube_shorts"  # Target platform for rendering safe zones
SPEAKER_A = "speaker_1"  # Dialogue speaker A
SPEAKER_B = "speaker_2"  # Dialogue speaker B


# --- 과도기 호환 함수 (Sprint B DB 마이그레이션 후 제거 예정) ---
_STRUCTURE_COERCE_MAP: dict[str, str] = {}
for _s in STRUCTURE_METADATA:
    _STRUCTURE_COERCE_MAP[_s.id] = _s.id  # "monologue" → "monologue"
    _STRUCTURE_COERCE_MAP[_s.label.lower()] = _s.id  # "monologue" → "monologue" (중복 무해)
    _STRUCTURE_COERCE_MAP[_s.label] = _s.id  # "Monologue" → "monologue"
    _STRUCTURE_COERCE_MAP[_s.label.lower().replace(" ", "_")] = _s.id  # "narrated_dialogue"
    _STRUCTURE_COERCE_MAP[_s.label.replace(" ", "_")] = _s.id  # "Narrated_Dialogue"

# 하위 호환: confession → monologue fallback
_STRUCTURE_COERCE_MAP["confession"] = "monologue"
_STRUCTURE_COERCE_MAP["Confession"] = "monologue"

_LANGUAGE_COERCE_MAP: dict[str, str] = {}
for _lang in LANGUAGE_METADATA:
    _LANGUAGE_COERCE_MAP[_lang.id] = _lang.id  # "korean" → "korean"
    _LANGUAGE_COERCE_MAP[_lang.id.title()] = _lang.id  # "Korean" → "korean"


def coerce_structure_id(value: str | None) -> str:
    """구조 문자열을 snake_case ID로 정규화. 인식 불가 시 DEFAULT_STRUCTURE 반환."""
    if not value:
        return DEFAULT_STRUCTURE
    stripped = value.strip()
    result = _STRUCTURE_COERCE_MAP.get(stripped)
    if result:
        return result
    # fallback: lowercase + underscore 변환 후 재시도
    normalized = stripped.lower().replace(" ", "_")
    return _STRUCTURE_COERCE_MAP.get(normalized, DEFAULT_STRUCTURE)


def coerce_tone_id(value: str | None) -> str:
    """톤 문자열을 정규화. 인식 불가 시 DEFAULT_TONE 반환."""
    if not value:
        return DEFAULT_TONE
    normalized = value.strip().lower()
    return normalized if normalized in TONE_IDS else DEFAULT_TONE


def coerce_language_id(value: str | None) -> str:
    """언어 문자열을 lowercase ID로 정규화. 인식 불가 시 DEFAULT_LANGUAGE 반환."""
    if not value:
        return DEFAULT_LANGUAGE
    stripped = value.strip()
    result = _LANGUAGE_COERCE_MAP.get(stripped)
    if result:
        return result
    return _LANGUAGE_COERCE_MAP.get(stripped.lower(), DEFAULT_LANGUAGE)


# --- Sentry Error Monitoring ---
SENTRY_DSN_BACKEND = os.getenv("SENTRY_DSN_BACKEND", "")
SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", os.getenv("APP_ENV", "development"))
SENTRY_TRACES_SAMPLE_RATE = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))

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
REFERENCE_ADAIN_WEIGHT_INDOOR = float(os.getenv("REFERENCE_ADAIN_WEIGHT_INDOOR", "0.30"))
REFERENCE_ADAIN_WEIGHT_OUTDOOR = float(os.getenv("REFERENCE_ADAIN_WEIGHT_OUTDOOR", "0.25"))
REFERENCE_ADAIN_GUIDANCE_END = float(os.getenv("REFERENCE_ADAIN_GUIDANCE_END", "0.5"))

# Reference AdaIN 충돌 시네마틱 태그 — AdaIN과 결합 시 형체 붕괴/색감 왜곡 유발
REFERENCE_ADAIN_CONFLICTING_TAGS: frozenset[str] = frozenset(
    {
        "depth_of_field",
        "shallow_depth_of_field",
        "bokeh",
        "blurry_background",
        "lens_flare",
        "chromatic_aberration",
    }
)

# Default pose/gaze/expression/mood/camera/emotion for ControlNet when Gemini omits context_tags
DEFAULT_POSE_TAG = "standing"
DEFAULT_GAZE_TAG = "looking_at_viewer"
DEFAULT_EXPRESSION_TAG = "smile"
DEFAULT_MOOD_TAG = "neutral"
DEFAULT_CAMERA_TAG = "cowboy_shot"
DEFAULT_EMOTION_TAG = "calm"
NARRATOR_FALLBACK_PROMPT = "no_humans, scenery"

# Finalize L2 검증: Cinematographer FORBIDDEN 목록 기반 금지 태그
PROHIBITED_IMAGE_TAGS: frozenset[str] = frozenset(
    {
        # 조합형 비표준 태그
        "cinematic_shadows",
        "computer_monitor",
        "glowing_screen",
        "dark_room",
        "high_contrast_shadow",
        # 감정 형용사 (비 Danbooru)
        "confident",
        "satisfied",
        "anxious",
        "tormented",
        "resigned",
        "paranoid",
        # 복합 expression
        "happy_smile",
        "sly_smile",
        "pensive_expression",
        "puzzled_expression",
        # 성별 태그 (시스템 자동 주입)
        "female",
        "male",
        # 제로 포스트 태그
        "bishoujo",
        "daylight",
        # 비표준 카메라/조명 (Rule 12 INVALID)
        "medium_shot",
        "rim_light",
        "dramatic_lighting",
        "cinematic_lighting",
        "warm_lighting",
        "cold_lighting",
    }
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
DEFAULT_USE_CONTROLNET = False  # 일반 씬 OFF (프롬프트 충성도 충분), 레퍼런스 생성만 ON
DEFAULT_CONTROLNET_WEIGHT = 0.8
DEFAULT_USE_IP_ADAPTER = False
DEFAULT_IP_ADAPTER_WEIGHT = 0.35  # IP-Adapter 기본 weight (ip_adapter_weight_b 기본값으로도 사용)
IP_ADAPTER_AUTO_ENABLE = True  # 레퍼런스 이미지 존재 시 자동 활성화
ENVIRONMENT_REFERENCE_ENABLED = (
    os.getenv("ENVIRONMENT_REFERENCE_ENABLED", "false").lower() == "true"
)  # True: background_id → Reference AdaIN 적용, False: 프롬프트 태그만
DEFAULT_REFERENCE_ONLY_WEIGHT = 0.5
DEFAULT_ENVIRONMENT_REFERENCE_WEIGHT = 0.3
MIN_IP_ADAPTER_WEIGHT_NO_LORA = 0.5  # LoRA 없는 캐릭터의 최소 IP-Adapter weight
DEFAULT_MULTI_GEN_ENABLED = False
DEFAULT_ENABLE_HR = False  # Hi-Res Fix 기본 비활성화 (StyleProfile에서 개별 활성화)

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
DEFAULT_IP_ADAPTER_GUIDANCE_END_VPRED = 0.5  # v-pred safety: 후반 50%는 모델 자체 처리 (0.7 → 색상 오염)
DEFAULT_IP_ADAPTER_WEIGHT_VPRED = 0.35  # v-pred safety weight (0.5 → PLUS preset에서 색상 오염 확인)

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
TTS_VOICE_CONSISTENCY_MODE = os.getenv("TTS_VOICE_CONSISTENCY_MODE", "true").lower() == "true"

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
TTS_MIN_SECS_PER_CHAR = float(
    os.getenv("TTS_MIN_SECS_PER_CHAR", "0.05")
)  # Truncation guard 하한 (0.05s/char = 20자/sec)
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
STORYBOARD_LANGUAGES = [{"value": lang.id, "label": lang.label} for lang in LANGUAGE_METADATA]
SHORTS_DURATIONS = [15, 30, 45, 60]

# --- Director Presets (SSOT for DirectorControlPanel) ---
# emotion 값은 EMOTION_VOCAB(services/agent/nodes/_context_tag_utils.py) 키의 서브셋
EMOTION_PRESETS: list[dict[str, str]] = [
    {"id": "excited", "label": "밝게", "emotion": "excited"},
    {"id": "calm", "label": "차분", "emotion": "calm"},
    {"id": "tense", "label": "긴장", "emotion": "tense"},
    {"id": "nostalgic", "label": "감성", "emotion": "nostalgic"},
]

BGM_MOOD_PRESETS: list[dict[str, str]] = [
    {"id": "upbeat", "label": "경쾌", "mood": "upbeat", "prompt": "bright upbeat cheerful background music"},
    {"id": "calm", "label": "잔잔", "mood": "calm", "prompt": "calm peaceful relaxing ambient music"},
    {"id": "tense", "label": "긴박", "mood": "tense", "prompt": "tense dramatic suspenseful cinematic music"},
    {
        "id": "romantic",
        "label": "로맨틱",
        "mood": "romantic",
        "prompt": "romantic warm emotional piano background music",
    },
]

# --- IP-Adapter Model Options (SSOT) ---
IP_ADAPTER_MODEL_OPTIONS: list[str] = ["clip_face", "clip"]

# --- Overlay Styles (SSOT for rendering + /presets) ---
OVERLAY_STYLE_OPTIONS: list[dict[str, str]] = [
    {"id": "overlay_minimal.png", "label": "Minimal"},
    {"id": "overlay_clean.png", "label": "Clean"},
    {"id": "overlay_bold.png", "label": "Bold"},
]
OVERLAY_STYLE_IDS: set[str] = {s["id"] for s in OVERLAY_STYLE_OPTIONS}

# --- Tag Group Descriptions (SSOT for /tags/groups) ---
TAG_GROUP_DESCRIPTIONS: dict[str, str] = {
    "quality": "품질 (masterpiece, best_quality)",
    "subject": "대상 (1girl, 1boy, solo)",
    "identity": "신원/캐릭터 (LoRA 트리거)",
    "hair_color": "머리 색 (blue_hair, blonde)",
    "hair_length": "머리 길이 (long/short_hair)",
    "hair_style": "헤어스타일 (ponytail, twintails)",
    "hair_accessory": "머리 장식 (hairpin, ribbon)",
    "eye_color": "눈 색 (blue_eyes, red_eyes)",
    "skin_color": "피부 색 (pale_skin)",
    "body_feature": "신체 특징 (elf_ears, wings)",
    "appearance": "외모 (freckles, makeup, tattoo)",
    "clothing": "의류/액세서리 (shirt, dress, shoes)",
    "expression": "표정 (smile, angry, blush)",
    "gaze": "시선 (looking_at_viewer)",
    "pose": "정적 자세 (standing, sitting)",
    "action": "동적 행동 (running, dancing)",
    "camera": "카메라/샷 (close_up, full_body)",
    "location_indoor": "실내 장소 (classroom, cafe)",
    "location_outdoor": "실외 장소 (beach, forest)",
    "environment": "소품/가구 (desk, computer, plant)",
    "background_type": "배경 타입 (white/simple_bg)",
    "time_weather": "시간/날씨 (day, night, rain)",
    "lighting": "조명 (sunlight, dramatic)",
    "mood": "분위기 (romantic, peaceful)",
    "style": "스타일 (anime, realistic)",
}

# --- Script Length Rules (SSOT for scriptwriter + creative_qc.py) ---
SCRIPT_LENGTH_KOREAN = (5, 35)  # (min_chars, max_chars)
SCRIPT_LENGTH_OTHER = (3, 18)  # (min_words, max_words)
SCENE_DURATION_RANGE = (2.0, 3.5)  # (min_seconds, max_seconds) per scene
SCENE_DEFAULT_DURATION = 3.0  # fallback duration for invalid scenes (revise node)
REVIEW_SCRIPT_MAX_CHARS_OTHER = 70  # char-level review threshold for non-Korean (~max_words * avg_chars)

# --- Dialogue Quality Patterns (Review L2 검증) ---
DIALOGUE_CLICHE_PATTERNS: list[str] = [
    r"심쿵",
    r"소름\s*돋",
    r"레전드",
    r"역대급",
    r"미쳤",
    r"대박",
    r"실화",
    r"ㄹㅇ",
    r"갓",
    r"킹",
    r"찐이",
    r"어떻게\s*이런",
    r"말이\s*돼\?",
    r"세상에",
    r"헐",
]

# --- Reading Speed (SSOT for duration estimation + Frontend display) ---
READING_SPEED: dict[str, dict] = {
    "korean": {"cps": 4.0, "unit": "chars"},
    "japanese": {"cps": 5.0, "unit": "chars"},
    "english": {"wps": 2.5, "unit": "words"},
}
READING_DURATION_PADDING = 0.5  # seconds (자연스러운 호흡 간격)
SCENE_DURATION_MAX = 10.0  # absolute safety cap per scene
DURATION_DEFICIT_THRESHOLD = 0.85  # 총 duration이 target의 이 비율 미만이면 부족으로 판정
DURATION_OVERFLOW_THRESHOLD = 1.3  # 총 duration이 target의 이 비율 초과이면 오버로 판정

# --- Interaction Mode Coercion (하위 호환) ---
_INTERACTION_MODE_MAP = {"auto": "fast_track", "hands_on": "guided"}
_VALID_INTERACTION_MODES = frozenset({"guided", "fast_track"})


def coerce_interaction_mode(value: str | None) -> str:
    """폐기된 interaction_mode 값을 현행 값으로 변환한다."""
    if not value:
        return "guided"
    normalized = value.strip().lower()
    mapped = _INTERACTION_MODE_MAP.get(normalized)
    if mapped:
        return mapped
    return normalized if normalized in _VALID_INTERACTION_MODES else "guided"


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
