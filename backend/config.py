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
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "password123")
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
SD_BATCH_CONCURRENCY = int(os.getenv("SD_BATCH_CONCURRENCY", "3"))

# --- Image Generation Defaults ---
# Optimized for Speed + Quality + Post/Full compatibility
# 512x768 (2:3) allows perfect 1:1 top-crop and full 9:16 cover
SD_DEFAULT_WIDTH = int(os.getenv("SD_DEFAULT_WIDTH", "512"))
SD_DEFAULT_HEIGHT = int(os.getenv("SD_DEFAULT_HEIGHT", "768"))
SD_DEFAULT_STEPS = int(os.getenv("SD_DEFAULT_STEPS", "28"))
SD_DEFAULT_CFG_SCALE = float(os.getenv("SD_DEFAULT_CFG_SCALE", "7.0"))
SD_DEFAULT_SAMPLER = os.getenv("SD_DEFAULT_SAMPLER", "DPM++ 2M Karras")

# --- LoRA Weight Cap ---
# Maximum weight for style LoRAs (applied to both character and narrator scenes)
STYLE_LORA_WEIGHT_CAP = float(os.getenv("STYLE_LORA_WEIGHT_CAP", "0.76"))

# --- SD API Timeouts (lightweight operations) ---
SD_API_TIMEOUT = float(os.getenv("SD_API_TIMEOUT", "10"))

# --- ControlNet Timeouts ---
CONTROLNET_API_TIMEOUT = float(os.getenv("CONTROLNET_API_TIMEOUT", "10"))
CONTROLNET_GENERATE_TIMEOUT = float(os.getenv("CONTROLNET_GENERATE_TIMEOUT", "180"))
CONTROLNET_DETECT_TIMEOUT = float(os.getenv("CONTROLNET_DETECT_TIMEOUT", "60"))

# --- Character Reference Generation ---
SD_REFERENCE_STEPS = int(os.getenv("SD_REFERENCE_STEPS", "25"))
SD_REFERENCE_CFG_SCALE = float(os.getenv("SD_REFERENCE_CFG_SCALE", "9.0"))
SD_REFERENCE_HR_UPSCALER = os.getenv("SD_REFERENCE_HR_UPSCALER", "R-ESRGAN 4x+ Anime6B")
SD_REFERENCE_DENOISING = float(os.getenv("SD_REFERENCE_DENOISING", "0.35"))

# --- External API ---
DANBOORU_API_BASE = os.getenv("DANBOORU_API_BASE", "https://danbooru.donmai.us")
DANBOORU_USER_AGENT = os.getenv("DANBOORU_USER_AGENT", "ShortsProducer/1.0")
DANBOORU_API_TIMEOUT = float(os.getenv("DANBOORU_API_TIMEOUT", "15"))
CIVITAI_API_BASE = os.getenv("CIVITAI_API_BASE", "https://civitai.com/api/v1")
CIVITAI_API_TIMEOUT = float(os.getenv("CIVITAI_API_TIMEOUT", "10"))

# --- Font & LoRA Defaults ---
DEFAULT_SCENE_TEXT_FONT = os.getenv("DEFAULT_SCENE_TEXT_FONT", "온글잎 박다현체.ttf")
DEFAULT_LORA_WEIGHT = float(os.getenv("DEFAULT_LORA_WEIGHT", "0.7"))

# --- Storyboard Defaults ---
DEFAULT_STRUCTURE = "Monologue"  # Options: "Monologue", "Dialogue"
DEFAULT_SPEAKER = "Narrator"  # Default speaker for scenes
SPEAKER_A = "A"  # Dialogue speaker A
SPEAKER_B = "B"  # Dialogue speaker B

API_PUBLIC_URL = os.getenv("API_PUBLIC_URL", "http://localhost:8000").rstrip("/")
if API_PUBLIC_URL == "http://localhost:8000":
    logger.info("Using default API_PUBLIC_URL: %s", API_PUBLIC_URL)

# --- Model Configuration ---
WD14_MODEL_DIR = pathlib.Path(os.getenv("WD14_MODEL_DIR", "models/wd14"))
WD14_THRESHOLD = float(os.getenv("WD14_THRESHOLD", "0.35"))

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
}

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

# --- Reference Image Generation Defaults ---
# Default prompts for generating IP-Adapter reference images
# Used when creating new characters without custom reference prompts
DEFAULT_REFERENCE_BASE_PROMPT = "masterpiece, best_quality, ultra-detailed, solo, full_body, (standing:1.2), portrait, facing_viewer, front_view, looking_at_viewer, straight_on, white_background, simple_background, plain_background, solid_background"
DEFAULT_REFERENCE_NEGATIVE_PROMPT = "lowres, (bad_anatomy:1.2), (bad_hands:1.2), text, error, missing_fingers, extra_digit, fewer_digits, cropped, worst_quality, low_quality, normal_quality, jpeg_artifacts, signature, watermark, username, blurry, easynegative, verybadimagenegative_v1.3, detailed_background, scenery, outdoors, indoors"

# Default negative prompt for scene generation (applied to Gemini-generated scenes)
DEFAULT_SCENE_NEGATIVE_PROMPT = "lowres, bad_anatomy, bad_hands, text, error, missing_fingers, extra_digit, fewer_digits, cropped, worst_quality, low_quality, jpeg_artifacts, signature, watermark, username, blurry, easynegative, verybadimagenegative_v1.3"

# Extra negative tags appended for Narrator scenes (no_humans) to suppress character generation
NARRATOR_NEGATIVE_PROMPT_EXTRA = "1girl, 1boy, 2girls, 2boys, multiple_girls, multiple_boys, person, human, male, female, solo, couple, face, portrait, upper_body, cowboy_shot"

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
FFMPEG_TIMEOUT_SECONDS = int(os.getenv("FFMPEG_TIMEOUT_SECONDS", "1200"))
RENDER_TASK_TTL_SECONDS = int(os.getenv("RENDER_TASK_TTL_SECONDS", "1800"))

# --- Text Extraction Defaults ---
CAPTION_MAX_LENGTH = int(os.getenv("CAPTION_MAX_LENGTH", "60"))

# --- IP-Adapter Defaults ---
# Default IP-Adapter settings (per-character overrides stored in DB)
# weight=0.35: POC 30-scene 실험 검증값 (clip_face + no BREAK 최적)
DEFAULT_CHARACTER_PRESET = {
    "weight": 0.35,
    "model": "clip_face",
}

# --- TTS Configuration ---
TTS_MODEL_NAME = os.getenv("TTS_MODEL_NAME", "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign")
TTS_PRELOAD_MODEL = os.getenv("TTS_PRELOAD_MODEL", "voice_design")  # "voice_design" (Clone removed)
TTS_DEFAULT_LANGUAGE = os.getenv("TTS_DEFAULT_LANGUAGE", "korean")
TTS_DEVICE = os.getenv("TTS_DEVICE", "auto")  # "auto" | "mps" | "cpu"
TTS_ATTN_IMPLEMENTATION = os.getenv("TTS_ATTN_IMPLEMENTATION", "sdpa")

# --- Voice Preset Configuration ---
VOICE_PRESET_MAX_FILE_SIZE = int(os.getenv("VOICE_PRESET_MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # 10MB
VOICE_PRESET_MIN_DURATION = float(os.getenv("VOICE_PRESET_MIN_DURATION", "3.0"))
VOICE_PRESET_MAX_DURATION = float(os.getenv("VOICE_PRESET_MAX_DURATION", "60.0"))
VOICE_PRESET_ALLOWED_FORMATS = {"wav", "mp3", "flac", "ogg"}

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

# --- TTS Audio Post-processing ---
TTS_AUDIO_TRIM_TOP_DB = int(
    os.getenv("TTS_AUDIO_TRIM_TOP_DB", "60")
)  # librosa.effects.trim threshold (removes trailing silence/hallucination)
TTS_AUDIO_FADE_MS = int(os.getenv("TTS_AUDIO_FADE_MS", "15"))  # Fade-in/out ms (removes click artifacts)
TTS_SILENCE_MAX_MS = int(os.getenv("TTS_SILENCE_MAX_MS", "300"))  # Internal silence max length (ms)

# --- TTS Quality Validation & Retry ---
TTS_MIN_DURATION_SEC = float(os.getenv("TTS_MIN_DURATION_SEC", "1.0"))  # Min TTS length (sec)
TTS_MAX_RETRIES = int(os.getenv("TTS_MAX_RETRIES", "2"))  # Retry count on quality failure

# --- TTS Performance ---
TTS_TIMEOUT_SECONDS = int(os.getenv("TTS_TIMEOUT_SECONDS", "120"))
TTS_CACHE_DIR = PROMPT_CACHE_DIR / "tts"
TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# --- Stable Audio Open (AI BGM) ---
SAO_MODEL_NAME = os.getenv("SAO_MODEL_NAME", "stabilityai/stable-audio-open-1.0")
SAO_DEVICE = os.getenv("SAO_DEVICE", "auto")
SAO_DEFAULT_DURATION = float(os.getenv("SAO_DEFAULT_DURATION", "30.0"))
SAO_MAX_DURATION = float(os.getenv("SAO_MAX_DURATION", "47.0"))
SAO_DEFAULT_STEPS = int(os.getenv("SAO_DEFAULT_STEPS", "100"))
SAO_SAMPLE_RATE = int(os.getenv("SAO_SAMPLE_RATE", "44100"))
SAO_CACHE_DIR = PROMPT_CACHE_DIR / "music"
SAO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
SAO_TIMEOUT_SECONDS = int(os.getenv("SAO_TIMEOUT_SECONDS", "120"))

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

# --- YouTube Upload Configuration ---
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")
YOUTUBE_REDIRECT_URI = os.getenv("YOUTUBE_REDIRECT_URI", "http://localhost:3000/manage?tab=youtube")
YOUTUBE_TOKEN_ENCRYPTION_KEY = os.getenv("YOUTUBE_TOKEN_ENCRYPTION_KEY", "")
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]
YOUTUBE_API_QUOTA_DAILY = int(os.getenv("YOUTUBE_API_QUOTA_DAILY", "10000"))
YOUTUBE_UPLOAD_COST = int(os.getenv("YOUTUBE_UPLOAD_COST", "1600"))

# --- Lab Configuration ---
LAB_DEFAULT_SD_STEPS = int(os.getenv("LAB_DEFAULT_SD_STEPS", "20"))
LAB_BATCH_MAX_SIZE = int(os.getenv("LAB_BATCH_MAX_SIZE", "20"))

# --- Creative Engine Configuration ---
CREATIVE_MAX_ROUNDS = int(os.getenv("CREATIVE_MAX_ROUNDS", "3"))
CREATIVE_LEADER_MODEL = os.getenv("CREATIVE_LEADER_MODEL", "gemini-2.0-flash")
CREATIVE_URL_FETCH_TIMEOUT = int(os.getenv("CREATIVE_URL_FETCH_TIMEOUT", "15"))
CREATIVE_URL_MAX_CONTENT_LENGTH = int(os.getenv("CREATIVE_URL_MAX_CONTENT_LENGTH", "5000"))
CREATIVE_URL_MAX_FETCH_COUNT = int(os.getenv("CREATIVE_URL_MAX_FETCH_COUNT", "3"))
CREATIVE_URL_MAX_RESPONSE_BYTES = int(os.getenv("CREATIVE_URL_MAX_RESPONSE_BYTES", str(1024 * 1024)))

# --- Creative Lab V2 Configuration ---
CREATIVE_DIRECTOR_SCORE_GAP_THRESHOLD = float(os.getenv("CREATIVE_DIRECTOR_SCORE_GAP_THRESHOLD", "0.15"))
CREATIVE_PIPELINE_MAX_RETRIES = int(os.getenv("CREATIVE_PIPELINE_MAX_RETRIES", "2"))
CREATIVE_MIN_CONCEPT_SCORE = float(os.getenv("CREATIVE_MIN_CONCEPT_SCORE", "0.6"))
CREATIVE_PIPELINE_POLL_INTERVAL_MS = int(os.getenv("CREATIVE_PIPELINE_POLL_INTERVAL_MS", "2000"))
CREATIVE_ZOMBIE_TIMEOUT_SECONDS = int(os.getenv("CREATIVE_ZOMBIE_TIMEOUT_SECONDS", "300"))

# Creative Lab: Agent Categories (SSOT for Frontend)
CREATIVE_AGENT_CATEGORIES = [
    {"value": "concept", "label": "Concept"},
    {"value": "production", "label": "Production"},
]

# Creative Lab: Agent-Template Mapping
CREATIVE_AGENT_TEMPLATES: dict[str, str] = {
    # Concept Phase
    "emotional_arc": "creative/concept_architect.j2",
    "visual_hook": "creative/concept_architect.j2",
    "narrative_twist": "creative/concept_architect.j2",
    "devils_advocate": "creative/devils_advocate.j2",
    "creative_director": "creative/director_evaluate.j2",
    "reference_analyst": "creative/reference_analyst.j2",
    # Production Phase
    "scriptwriter": "creative/scriptwriter.j2",
    "cinematographer": "creative/cinematographer.j2",
    "sound_designer": "creative/sound_designer.j2",
    "copyright_reviewer": "creative/copyright_reviewer.j2",
}

# --- Ollama (Local LLM) Configuration ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
OLLAMA_DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "exaone3.5:7.8b")
