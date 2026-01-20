from __future__ import annotations

import base64
import io
import csv
import hashlib
import json
import logging
import os
import pathlib
import re
import shutil
import subprocess
import textwrap
import time
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types
import httpx
from jinja2 import Environment, FileSystemLoader
import numpy as np
import onnxruntime as ort
from pydantic import BaseModel, ConfigDict
import edge_tts
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

load_dotenv()

LOG_FILE = os.getenv("LOG_FILE", "logs/backend.log")
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "1").lower() not in {"0", "false", "no"}
handlers = [logging.StreamHandler()]
if LOG_TO_FILE:
    log_path = pathlib.Path(LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handlers.append(logging.FileHandler(log_path, encoding="utf-8"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=handlers,
)
logger = logging.getLogger("backend")
if LOG_TO_FILE:
    log_path = pathlib.Path(LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(file_handler)
        logger.propagate = True
        logger.info("File logging enabled: %s", log_path)

OUTPUT_DIR = pathlib.Path("outputs")
IMAGE_DIR = OUTPUT_DIR / "images"
VIDEO_DIR = OUTPUT_DIR / "videos"
CACHE_DIR = OUTPUT_DIR / "cache"
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "86400"))
ASSETS_DIR = pathlib.Path("assets")
AUDIO_DIR = ASSETS_DIR / "audio"
OVERLAY_DIR = ASSETS_DIR / "overlay"

for d in (OUTPUT_DIR, IMAGE_DIR, VIDEO_DIR, CACHE_DIR, AUDIO_DIR, OVERLAY_DIR):
    d.mkdir(parents=True, exist_ok=True)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)

app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

BASE_DIR = pathlib.Path(__file__).resolve().parent
template_env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates")))
SD_BASE_URL = os.getenv("SD_BASE_URL", "http://127.0.0.1:7860")
SD_TXT2IMG_URL = f"{SD_BASE_URL}/sdapi/v1/txt2img"
SD_MODELS_URL = f"{SD_BASE_URL}/sdapi/v1/sd-models"
SD_OPTIONS_URL = f"{SD_BASE_URL}/sdapi/v1/options"
SD_TIMEOUT_SECONDS = float(os.getenv("SD_TIMEOUT_SECONDS", "600"))
WD14_MODEL_DIR = pathlib.Path(os.getenv("WD14_MODEL_DIR", "models/wd14"))
WD14_THRESHOLD = float(os.getenv("WD14_THRESHOLD", "0.35"))

_WD14_SESSION: ort.InferenceSession | None = None
_WD14_TAGS: list[str] | None = None
_WD14_TAG_CATEGORIES: list[str] | None = None
_KEYWORD_SYNONYMS: dict[str, set[str]] = {}
_KEYWORD_IGNORE: set[str] = set()
_KEYWORD_CATEGORIES: dict[str, list[str]] = {}


class StoryboardRequest(BaseModel):
    topic: str
    duration: int = 10
    style: str = "Anime"
    language: str = "Korean"
    structure: str = "Monologue"
    actor_a_gender: str = "female"


class StoryboardScene(BaseModel):
    scene_id: int
    script: str
    speaker: str = "Narrator"
    duration: float = 3
    image_prompt: str = ""
    image_prompt_ko: str = ""

    model_config = ConfigDict(extra="allow")


class VideoScene(BaseModel):
    image_url: str
    script: str = ""
    speaker: str = "Narrator"
    duration: float = 3

    model_config = ConfigDict(extra="allow")


class OverlaySettings(BaseModel):
    enabled: bool = False
    profile_name: str = "daily_shorts"
    likes_count: str = "12.5k"
    caption: str = "Amazing video! #shorts"
    frame_style: str = "overlay_minimal.png"


class VideoRequest(BaseModel):
    scenes: list[VideoScene]
    project_name: str = "my_shorts"
    bgm_file: str | None = None
    width: int = 1080
    height: int = 1920
    layout_style: str = "full"
    motion_style: str = "none"
    narrator_voice: str = "ko-KR-SunHiNeural"
    speed_multiplier: float = 1.0
    include_subtitles: bool = True
    overlay_settings: OverlaySettings | None = None


class SceneGenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    steps: int = 24
    cfg_scale: float = 7.0
    sampler_name: str = "DPM++ 2M Karras"
    seed: int = -1
    width: int = 512
    height: int = 512
    clip_skip: int = 2
    enable_hr: bool = False
    hr_scale: float = 1.5
    hr_upscaler: str = "Latent"
    hr_second_pass_steps: int = 10
    denoising_strength: float = 0.25


class SceneValidateRequest(BaseModel):
    image_b64: str
    prompt: str = ""
    mode: str = "wd14"


class PromptRewriteRequest(BaseModel):
    base_prompt: str
    scene_prompt: str
    style: str = "Anime"
    mode: str = "compose"


class PromptSplitRequest(BaseModel):
    example_prompt: str
    style: str = "Anime"


class SDModelRequest(BaseModel):
    sd_model_checkpoint: str


class KeywordApproveRequest(BaseModel):
    tag: str
    category: str

def decode_data_url(data_url: str) -> bytes:
    if not data_url:
        raise ValueError("Empty image data")
    b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
    return base64.b64decode(b64)


def normalize_prompt_token(token: str) -> str:
    cleaned = token.strip()
    if not cleaned:
        return ""
    if cleaned.startswith("<") and cleaned.endswith(">"):
        return ""
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = cleaned[1:-1]
    cleaned = re.sub(r":[0-9.]+$", "", cleaned)
    cleaned = cleaned.replace("_", " ")
    return cleaned.strip().lower()


def load_keyword_map() -> tuple[dict[str, set[str]], set[str], dict[str, list[str]]]:
    global _KEYWORD_SYNONYMS, _KEYWORD_IGNORE, _KEYWORD_CATEGORIES
    if _KEYWORD_SYNONYMS or _KEYWORD_IGNORE or _KEYWORD_CATEGORIES:
        return _KEYWORD_SYNONYMS, _KEYWORD_IGNORE, _KEYWORD_CATEGORIES

    keyword_path = BASE_DIR / "keywords.json"
    if not keyword_path.exists():
        return {}, set(), {}
    data = json.loads(keyword_path.read_text(encoding="utf-8"))
    synonyms: dict[str, set[str]] = {}
    for key, values in (data.get("synonyms") or {}).items():
        base = normalize_prompt_token(key)
        if not base:
            continue
        entries = {base}
        for value in values or []:
            normalized = normalize_prompt_token(value)
            if normalized:
                entries.add(normalized)
        synonyms[base] = entries
    ignore = {normalize_prompt_token(item) for item in data.get("ignore", [])}
    categories = {}
    for key, values in (data.get("categories") or {}).items():
        normalized = [normalize_prompt_token(item) for item in (values or [])]
        categories[key] = [item for item in normalized if item]
    _KEYWORD_SYNONYMS = synonyms
    _KEYWORD_IGNORE = {item for item in ignore if item}
    _KEYWORD_CATEGORIES = categories
    return _KEYWORD_SYNONYMS, _KEYWORD_IGNORE, _KEYWORD_CATEGORIES


def expand_synonyms(tokens: list[str]) -> set[str]:
    synonyms_map, _, _ = load_keyword_map()
    expanded: set[str] = set()
    for token in tokens:
        if not token:
            continue
        expanded.add(token)
        if token in synonyms_map:
            expanded.update(synonyms_map[token])
    return expanded


def load_known_keywords() -> set[str]:
    synonyms_map, ignore_tokens, categories = load_keyword_map()
    known: set[str] = set(ignore_tokens)
    for values in categories.values():
        known.update(values)
    for key, values in synonyms_map.items():
        known.add(key)
        known.update(values)
    return {token for token in known if token}


def update_keyword_suggestions(unknown_tags: list[str]) -> None:
    if not unknown_tags:
        return
    suggestions_path = CACHE_DIR / "keyword_suggestions.json"
    try:
        if suggestions_path.exists():
            data = json.loads(suggestions_path.read_text(encoding="utf-8"))
        else:
            data = {}
        for tag in unknown_tags:
            data[tag] = int(data.get(tag, 0)) + 1
        suggestions_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception:
        logger.exception("Failed to update keyword suggestions")


def reset_keyword_cache() -> None:
    global _KEYWORD_SYNONYMS, _KEYWORD_IGNORE, _KEYWORD_CATEGORIES
    _KEYWORD_SYNONYMS = {}
    _KEYWORD_IGNORE = set()
    _KEYWORD_CATEGORIES = {}


def load_keywords_file() -> dict[str, Any]:
    keyword_path = BASE_DIR / "keywords.json"
    if not keyword_path.exists():
        raise FileNotFoundError("keywords.json not found")
    return json.loads(keyword_path.read_text(encoding="utf-8"))


def save_keywords_file(data: dict[str, Any]) -> None:
    keyword_path = BASE_DIR / "keywords.json"
    keyword_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def load_keyword_suggestions(min_count: int = 1, limit: int = 50) -> list[dict[str, Any]]:
    suggestions_path = CACHE_DIR / "keyword_suggestions.json"
    if not suggestions_path.exists():
        return []
    try:
        data = json.loads(suggestions_path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to read keyword suggestions")
        return []
    known = load_known_keywords()
    items = [
        {"tag": tag, "count": int(count)}
        for tag, count in data.items()
        if int(count) >= min_count and tag not in known
    ]
    items.sort(key=lambda item: (-item["count"], item["tag"]))
    return items[:max(1, limit)]


def format_keyword_context() -> str:
    _, _, categories = load_keyword_map()
    if not categories:
        return ""
    lines = ["Allowed Keywords (use exactly as written):"]
    for key in sorted(categories.keys()):
        values = categories[key]
        if not values:
            continue
        lines.append(f"- {key}: {', '.join(values)}")
    return "\n".join(lines)


def filter_prompt_tokens(prompt: str) -> str:
    synonyms_map, ignore_tokens, categories = load_keyword_map()
    allowed = {token for values in categories.values() for token in values}
    if not allowed:
        return normalize_prompt_tokens(prompt)
    synonym_lookup = {
        variant: base
        for base, variants in synonyms_map.items()
        for variant in variants
    }
    tokens = split_prompt_tokens(prompt)
    cleaned: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        normalized = normalize_prompt_token(token)
        if not normalized or normalized in ignore_tokens:
            continue
        base = None
        if normalized in allowed:
            base = normalized
        elif normalized in synonym_lookup and synonym_lookup[normalized] in allowed:
            base = synonym_lookup[normalized]
        if base and base not in seen:
            cleaned.append(base)
            seen.add(base)
    return ", ".join(cleaned)


def parse_json_payload(text: str) -> dict[str, Any]:
    cleaned = text.strip().replace("```json", "").replace("```", "")
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start:end + 1]
    return json.loads(cleaned)


def resolve_image_mime(image: Image.Image) -> str:
    fmt = (image.format or "PNG").upper()
    if fmt == "JPEG":
        return "image/jpeg"
    if fmt == "WEBP":
        return "image/webp"
    return "image/png"


def load_wd14_model() -> tuple[ort.InferenceSession, list[str], list[str]]:
    global _WD14_SESSION, _WD14_TAGS, _WD14_TAG_CATEGORIES
    if _WD14_SESSION and _WD14_TAGS and _WD14_TAG_CATEGORIES:
        return _WD14_SESSION, _WD14_TAGS, _WD14_TAG_CATEGORIES

    model_path = WD14_MODEL_DIR / "model.onnx"
    tags_path = WD14_MODEL_DIR / "selected_tags.csv"
    if not model_path.exists() or not tags_path.exists():
        raise FileNotFoundError("WD14 model files not found.")

    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    tags: list[str] = []
    categories: list[str] = []
    with tags_path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        name_idx = 1
        category_idx = 2
        if headers:
            lowered = [h.strip().lower() for h in headers]
            if "name" in lowered:
                name_idx = lowered.index("name")
            if "category" in lowered:
                category_idx = lowered.index("category")
        for row in reader:
            if len(row) <= max(name_idx, category_idx):
                continue
            tag = row[name_idx].replace("_", " ").strip()
            category = row[category_idx].strip()
            tags.append(tag)
            categories.append(category)

    _WD14_SESSION = session
    _WD14_TAGS = tags
    _WD14_TAG_CATEGORIES = categories
    return session, tags, categories


def wd14_predict_tags(image: Image.Image, threshold: float) -> list[dict[str, Any]]:
    session, tags, categories = load_wd14_model()
    image = image.convert("RGBA")
    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    image = Image.alpha_composite(background, image).convert("RGB")
    image = image.resize((448, 448), Image.LANCZOS)
    img_array = np.array(image).astype(np.float32)
    img_array = img_array[:, :, ::-1]
    img_array = img_array / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    inputs = {session.get_inputs()[0].name: img_array}
    preds = session.run([session.get_outputs()[0].name], inputs)[0][0]

    results: list[dict[str, Any]] = []
    for score, tag, category in zip(preds, tags, categories):
        if category == "9":
            continue
        if score < threshold:
            continue
        results.append({"tag": tag, "score": float(score), "category": category})

    results.sort(key=lambda item: item["score"], reverse=True)
    return results


def gemini_predict_tags(image: Image.Image) -> list[dict[str, Any]]:
    if not gemini_client:
        raise RuntimeError("Gemini key missing")

    mime_type = resolve_image_mime(image)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    image_bytes = buf.getvalue()
    instruction = (
        "Analyze the image and return JSON only: "
        "{\"tags\": [\"short tag\", ...]}. "
        "Use Stable Diffusion tag-style nouns/adjectives, no sentences."
    )
    res = gemini_client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            instruction,
        ],
    )
    data = parse_json_payload(res.text)
    tags = data.get("tags", [])
    results: list[dict[str, Any]] = []
    for tag in tags:
        if not isinstance(tag, str):
            continue
        cleaned = tag.strip()
        if not cleaned:
            continue
        results.append({"tag": cleaned, "score": 1.0, "category": "gemini"})
    return results


def compare_prompt_to_tags(prompt: str, tags: list[dict[str, Any]]) -> dict[str, Any]:
    raw_tokens = split_prompt_tokens(prompt)
    skip_tokens = {
        "best quality",
        "masterpiece",
        "high quality",
        "ultra detailed",
        "ultra detail",
        "highres",
        "8k",
        "4k",
        "photorealistic",
        "realistic",
        "stylized",
        "anime",
        "illustration",
        "digital painting",
        "artstation",
        "sharp focus",
        "cinematic",
    }
    tokens = [normalize_prompt_token(token) for token in raw_tokens]
    synonyms_map, ignore_tokens, _ = load_keyword_map()
    tokens = [token for token in tokens if token and token not in skip_tokens and token not in ignore_tokens]
    if not tokens:
        return {"matched": [], "missing": [], "extra": []}

    tag_names = [item["tag"].lower() for item in tags]
    tag_set = set(tag_names)
    expanded_tags = expand_synonyms(list(tag_set))

    matched: list[str] = []
    missing: list[str] = []
    for token in tokens:
        if token in expanded_tags or any(token in tag for tag in tag_set):
            matched.append(token)
        else:
            missing.append(token)

    extra = []
    for item in tags[:20]:
        name = normalize_prompt_token(item["tag"])
        if not name or name in ignore_tokens:
            continue
        if name not in expand_synonyms(tokens):
            extra.append(item["tag"])

    return {"matched": matched, "missing": missing, "extra": extra}


def cache_key_for_validation(image_bytes: bytes, prompt: str, mode: str) -> str:
    digest = hashlib.sha256()
    digest.update(image_bytes)
    digest.update(prompt.encode("utf-8"))
    digest.update(mode.encode("utf-8"))
    return digest.hexdigest()


def scrub_payload(payload: dict[str, Any]) -> dict[str, Any]:
    redacted = {}
    for key, value in payload.items():
        if key in {"image_url", "image", "image_b64"} and isinstance(value, str):
            redacted[key] = "<redacted>"
        elif isinstance(value, list):
            redacted[key] = [
                scrub_payload(item) if isinstance(item, dict) else item for item in value
            ]
        elif isinstance(value, dict):
            redacted[key] = scrub_payload(value)
        else:
            redacted[key] = value
    return redacted


def wrap_text(text: str, width: int) -> str:
    if not text:
        return ""
    return "\n".join(textwrap.wrap(text, width=width))


def to_edge_tts_rate(multiplier: float) -> str:
    safe_multiplier = max(0.1, min(multiplier, 2.0))
    percent = int(round((safe_multiplier - 1.0) * 100))
    return f"+{percent}%" if percent >= 0 else f"{percent}%"


def split_prompt_tokens(prompt: str) -> list[str]:
    return [token.strip() for token in prompt.split(",") if token.strip()]


def merge_prompt_tokens(primary: list[str], secondary: list[str]) -> str:
    seen = set()
    merged: list[str] = []
    for token in primary + secondary:
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(token)
    return ", ".join(merged)


def is_scene_token(token: str) -> bool:
    keywords = [
        "sitting", "standing", "walking", "running", "jumping", "kneeling", "crouching", "lying",
        "from above", "top-down", "low angle", "high angle", "close-up", "wide shot", "full body",
        "library", "cafe", "street", "room", "bedroom", "office", "classroom", "park", "forest",
        "beach", "city", "night", "sunset", "sunrise", "rain", "snow", "background", "lighting",
        "indoors", "outdoors"
    ]
    lower = token.lower()
    return any(keyword in lower for keyword in keywords)


def normalize_prompt_tokens(prompt: str) -> str:
    lora_tags = re.findall(r"<lora:[^>]+>", prompt, flags=re.IGNORECASE)
    model_tags = re.findall(r"<model:[^>]+>", prompt, flags=re.IGNORECASE)

    def unique_tags(tags: list[str]) -> list[str]:
        seen = set()
        ordered: list[str] = []
        for tag in tags:
            key = tag.lower()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(tag)
        return ordered

    unique_lora = unique_tags(lora_tags)
    unique_model = unique_tags(model_tags)
    cleaned = re.sub(r"<lora:[^>]+>", "", prompt, flags=re.IGNORECASE)
    cleaned = re.sub(r"<model:[^>]+>", "", cleaned, flags=re.IGNORECASE)
    tokens = split_prompt_tokens(cleaned)
    seen = set()
    merged: list[str] = []
    for token in tokens:
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(token)
    merged.extend(unique_lora)
    merged.extend(unique_model)
    return ", ".join(merged)


def normalize_negative_prompt(negative: str) -> str:
    tokens = split_prompt_tokens(negative)
    seen = set()
    merged: list[str] = []
    for token in tokens:
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(token)
    return ", ".join(merged)


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
    if not os.path.exists(font_path):
        font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
    try:
        return ImageFont.truetype(font_path, size=size)
    except Exception:
        return ImageFont.load_default()


def _draw_text_with_stroke(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    stroke_width: int = 2,
    stroke_fill: tuple[int, int, int, int] = (0, 0, 0, 255),
) -> None:
    draw.text(xy, text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)


def _draw_common_content(
    draw: ImageDraw.ImageDraw,
    width: int,
    height: int,
    settings: OverlaySettings,
    safe_margin: int,
    header_top: int,
    header_height: int,
    footer_top: int,
    footer_height: int,
    use_stroke: bool = False,
    text_color: tuple[int, int, int, int] = (255, 255, 255, 235),
    sub_color: tuple[int, int, int, int] = (200, 200, 200, 220),
    offset_x: int = 0,
    offset_y: int = 0,
) -> None:
    avatar_radius = int(header_height * 0.35)
    avatar_center = (
        offset_x + safe_margin + avatar_radius + 18,
        offset_y + header_top + header_height // 2,
    )

    draw.ellipse(
        (
            avatar_center[0] - avatar_radius,
            avatar_center[1] - avatar_radius,
            avatar_center[0] + avatar_radius,
            avatar_center[1] + avatar_radius,
        ),
        fill=(255, 255, 255, 255),
        outline=(0, 0, 0, 255) if use_stroke or text_color == (0, 0, 0, 255) else None,
        width=2 if (use_stroke or text_color == (0, 0, 0, 255)) else 0,
    )

    name_font = _get_font(int(header_height * 0.28))
    small_font = _get_font(int(header_height * 0.2))
    caption_font = _get_font(int(footer_height * 0.22))
    avatar_font = _get_font(int(header_height * 0.26))

    name_x = avatar_center[0] + avatar_radius + 16
    name_y = offset_y + header_top + int(header_height * 0.18)

    stroke_width = 3 if use_stroke else 0
    stroke_fill = (0, 0, 0, 255)

    if use_stroke:
        _draw_text_with_stroke(
            draw,
            (name_x, name_y),
            settings.profile_name,
            name_font,
            text_color,
            stroke_width,
            stroke_fill,
        )
        _draw_text_with_stroke(
            draw,
            (name_x, name_y + int(header_height * 0.38)),
            f"{settings.likes_count} likes",
            small_font,
            sub_color,
            stroke_width,
            stroke_fill,
        )
    else:
        draw.text((name_x, name_y), settings.profile_name, fill=text_color, font=name_font)
        draw.text(
            (name_x, name_y + int(header_height * 0.38)),
            f"{settings.likes_count} likes",
            fill=sub_color,
            font=small_font,
        )

    initial = (settings.profile_name.strip()[:1] or "A").upper()
    init_w, init_h = draw.textbbox((0, 0), initial, font=avatar_font)[2:]
    draw.text(
        (avatar_center[0] - init_w / 2, avatar_center[1] - init_h / 2),
        initial,
        fill=(30, 30, 30, 255),
        font=avatar_font,
    )

    caption_text = settings.caption or ""
    caption_lines = textwrap.wrap(caption_text, width=26)[:2]
    caption_y = offset_y + footer_top + int(footer_height * 0.2)
    for idx, line in enumerate(caption_lines):
        y_pos = caption_y + idx * int(footer_height * 0.32)
        if use_stroke:
            _draw_text_with_stroke(
                draw,
                (offset_x + safe_margin + 20, y_pos),
                line,
                caption_font,
                text_color,
                stroke_width,
                stroke_fill,
            )
        else:
            draw.text((offset_x + safe_margin + 20, y_pos), line, fill=text_color, font=caption_font)


def _draw_clean_overlay(
    draw: ImageDraw.ImageDraw,
    width: int,
    height: int,
    settings: OverlaySettings,
    offset_x: int = 0,
    offset_y: int = 0,
) -> None:
    safe_margin = int(width * 0.06)
    header_top = int(height * 0.06)
    header_height = int(height * 0.1)
    footer_top = int(height * 0.78)
    footer_height = int(height * 0.14)

    header_box = (
        offset_x + safe_margin,
        offset_y + header_top,
        offset_x + width - safe_margin,
        offset_y + header_top + header_height,
    )
    footer_box = (
        offset_x + safe_margin,
        offset_y + footer_top,
        offset_x + width - safe_margin,
        offset_y + footer_top + footer_height,
    )

    draw.rounded_rectangle(header_box, radius=28, fill=(10, 10, 10, 170))
    draw.rounded_rectangle(footer_box, radius=28, fill=(10, 10, 10, 170))

    _draw_common_content(
        draw,
        width,
        height,
        settings,
        safe_margin,
        header_top,
        header_height,
        footer_top,
        footer_height,
        offset_x=offset_x,
        offset_y=offset_y,
    )


def _draw_minimal_overlay(
    draw: ImageDraw.ImageDraw,
    width: int,
    height: int,
    settings: OverlaySettings,
    offset_x: int = 0,
    offset_y: int = 0,
) -> None:
    safe_margin = int(width * 0.06)
    header_top = int(height * 0.06)
    header_height = int(height * 0.1)
    footer_top = int(height * 0.78)
    footer_height = int(height * 0.14)

    _draw_common_content(
        draw,
        width,
        height,
        settings,
        safe_margin,
        header_top,
        header_height,
        footer_top,
        footer_height,
        use_stroke=True,
        offset_x=offset_x,
        offset_y=offset_y,
    )


def _draw_bold_overlay(
    draw: ImageDraw.ImageDraw,
    width: int,
    height: int,
    settings: OverlaySettings,
    offset_x: int = 0,
    offset_y: int = 0,
) -> None:
    safe_margin = int(width * 0.06)
    header_top = int(height * 0.06)
    header_height = int(height * 0.1)
    footer_top = int(height * 0.78)
    footer_height = int(height * 0.14)

    header_box = (
        offset_x + safe_margin,
        offset_y + header_top,
        offset_x + width - safe_margin,
        offset_y + header_top + header_height,
    )
    footer_box = (
        offset_x + safe_margin,
        offset_y + footer_top,
        offset_x + width - safe_margin,
        offset_y + footer_top + footer_height,
    )

    draw.rounded_rectangle(
        header_box, radius=16, fill=(255, 235, 59, 240), outline=(0, 0, 0, 255), width=4
    )
    draw.rounded_rectangle(
        footer_box, radius=16, fill=(255, 255, 255, 240), outline=(0, 0, 0, 255), width=4
    )

    _draw_common_content(
        draw,
        width,
        height,
        settings,
        safe_margin,
        header_top,
        header_height,
        footer_top,
        footer_height,
        text_color=(0, 0, 0, 255),
        sub_color=(60, 60, 60, 255),
        offset_x=offset_x,
        offset_y=offset_y,
    )


def create_overlay_image(
    settings: OverlaySettings,
    width: int,
    height: int,
    output_path: pathlib.Path,
    layout_style: str = "full",
) -> None:
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    offset_x = 0
    offset_y = 0
    frame_w = width
    frame_h = height
    if layout_style == "post":
        frame_w = int(width * 0.86)
        frame_h = frame_w
        offset_x = (width - frame_w) // 2
        offset_y = (height - frame_h) // 2

    if settings.frame_style == "overlay_minimal.png":
        _draw_minimal_overlay(draw, frame_w, frame_h, settings, offset_x, offset_y)
    elif settings.frame_style == "overlay_bold.png":
        _draw_bold_overlay(draw, frame_w, frame_h, settings, offset_x, offset_y)
    else:
        _draw_clean_overlay(draw, frame_w, frame_h, settings, offset_x, offset_y)

    canvas.save(output_path, "PNG")


def resolve_overlay_frame(
    settings: OverlaySettings,
    width: int,
    height: int,
    output_path: pathlib.Path,
    layout_style: str = "full",
) -> None:
    known_styles = {"overlay_minimal.png", "overlay_clean.png", "overlay_bold.png"}
    if settings.frame_style not in known_styles:
        frame_dir = OVERLAY_DIR
        candidate = frame_dir / settings.frame_style
        if candidate.exists():
            try:
                frame = Image.open(candidate).convert("RGBA")
                if frame.size != (width, height):
                    frame = frame.resize((width, height), Image.LANCZOS)
                frame.save(output_path, "PNG")
                return
            except Exception:
                pass
    create_overlay_image(settings, width, height, output_path, layout_style)


def compose_post_frame(
    image_bytes: bytes,
    width: int,
    height: int,
    profile_name: str,
    caption: str,
    font_path: str,
) -> Image.Image:
    image = Image.open(io.BytesIO(image_bytes))
    image_rgb = image.convert("RGB")
    background = ImageOps.fit(image_rgb, (width, height), Image.LANCZOS)
    background = background.filter(ImageFilter.GaussianBlur(radius=24)).convert("RGBA")
    background.alpha_composite(Image.new("RGBA", (width, height), (0, 0, 0, 20)))

    card_size = int(width * 0.86)
    card_padding = int(card_size * 0.06)
    radius = int(card_size * 0.08)
    header_height = int(card_size * 0.14)
    caption_height = int(card_size * 0.18)
    card = Image.new("RGBA", (card_size, card_size), (255, 255, 255, 245))
    mask = Image.new("L", (card_size, card_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, card_size, card_size), radius=radius, fill=255)
    card.putalpha(mask)

    shadow = Image.new("RGBA", (card_size, card_size), (0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=18))

    card_x = (width - card_size) // 2
    card_y = (height - card_size) // 2
    background.alpha_composite(shadow, (card_x, card_y + 10))
    background.alpha_composite(card, (card_x, card_y))

    inner_width = card_size - (card_padding * 2)
    image_area = inner_width
    image_area = min(image_area, card_size - (card_padding * 2 + header_height + caption_height))
    image_area = max(image_area, int(card_size * 0.4))
    image_x = card_x + card_padding
    image_y = card_y + card_padding + header_height

    inner = ImageOps.fit(image_rgb, (image_area, image_area), Image.LANCZOS).convert("RGBA")
    background.alpha_composite(inner, (image_x, image_y))

    draw = ImageDraw.Draw(background)
    try:
        name_font = ImageFont.truetype(font_path, size=int(card_size * 0.05))
        meta_font = ImageFont.truetype(font_path, size=int(card_size * 0.035))
        caption_font = ImageFont.truetype(font_path, size=int(card_size * 0.045))
    except Exception:
        name_font = ImageFont.load_default()
        meta_font = ImageFont.load_default()
        caption_font = ImageFont.load_default()

    profile_radius = int(card_size * 0.045)
    profile_center = (card_x + card_padding + profile_radius, card_y + card_padding + profile_radius)
    draw.ellipse(
        (
            profile_center[0] - profile_radius,
            profile_center[1] - profile_radius,
            profile_center[0] + profile_radius,
            profile_center[1] + profile_radius,
        ),
        fill=(245, 210, 140),
        outline=(255, 255, 255),
        width=2,
    )
    initial = (profile_name.strip()[:1] or "A").upper()
    text_w, text_h = draw.textbbox((0, 0), initial, font=meta_font)[2:]
    draw.text(
        (profile_center[0] - text_w / 2, profile_center[1] - text_h / 2),
        initial,
        fill=(80, 60, 40),
        font=meta_font,
    )
    name_x = profile_center[0] + profile_radius + int(card_size * 0.03)
    name_y = card_y + card_padding + int(card_size * 0.015)
    draw.text((name_x, name_y), profile_name or "creator", fill=(40, 40, 40), font=name_font)
    draw.text(
        (name_x, name_y + int(card_size * 0.05)),
        "• 1m",
        fill=(150, 150, 150),
        font=meta_font,
    )

    caption_text = caption.strip()
    if caption_text:
        caption_width = max(18, int(card_size * 0.08))
        caption_lines = textwrap.wrap(caption_text, width=caption_width)[:2]
        cap_x = card_x + card_padding
        cap_y = card_y + card_size - caption_height + int(card_size * 0.02)
        for idx, line in enumerate(caption_lines):
            draw.text(
                (cap_x, cap_y + idx * int(card_size * 0.05)),
                line,
                fill=(60, 60, 60),
                font=caption_font,
            )

    return background.convert("RGB")


def apply_post_overlay_mask(overlay_path: pathlib.Path, width: int, height: int) -> None:
    try:
        overlay = Image.open(overlay_path).convert("RGBA")
    except Exception:
        return

    card_size = int(width * 0.86)
    radius = int(card_size * 0.08)
    card_x = (width - card_size) // 2
    card_y = (height - card_size) // 2

    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        (card_x, card_y, card_x + card_size, card_y + card_size),
        radius=radius,
        fill=255,
    )
    base_alpha = overlay.getchannel("A")
    non_black = ImageOps.grayscale(overlay.convert("RGB")).point(lambda v: 0 if v < 5 else 255)
    alpha = ImageChops.multiply(base_alpha, non_black)
    overlay.putalpha(ImageChops.multiply(alpha, mask))
    overlay.save(overlay_path, "PNG")


@app.get("/audio/list")
async def get_audio_list():
    logger.info("📥 [Audio List]")
    files = []
    for ext in ("*.mp3", "*.MP3", "*.wav", "*.WAV", "*.m4a", "*.M4A"):
        for f in AUDIO_DIR.glob(ext):
            files.append({"name": f.name, "url": f"http://localhost:8000/assets/audio/{f.name}"})
    return {"audios": sorted(files, key=lambda x: x["name"])}


@app.post("/storyboard/create")
async def create_storyboard(request: StoryboardRequest):
    logger.info("📥 [Storyboard Req] %s", request.model_dump())
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini key missing")
    try:
        template = template_env.get_template("create_storyboard.j2")
        system_instruction = (
            "SYSTEM: You are a professional storyboarder and scriptwriter. "
            "Write concise, punchy scripts in the requested language (max 40 chars). "
            "No emojis. Use ONLY the allowed keywords list for image_prompt tags. "
            "Do not invent new tags. Return raw JSON only."
        )
        rendered = template.render(
            topic=request.topic,
            duration=request.duration,
            style=request.style,
            structure=request.structure,
            language=request.language,
            keyword_context=format_keyword_context(),
        )
        res = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=f"{system_instruction}\n\n{rendered}",
        )
        scenes = json.loads(res.text.strip().replace("```json", "").replace("```", ""))
        for scene in scenes:
            raw_prompt = scene.get("image_prompt", "")
            if not raw_prompt:
                continue
            filtered = filter_prompt_tokens(raw_prompt)
            if not filtered:
                logger.warning("No allowed keywords in scene prompt; using normalized original.")
                filtered = normalize_prompt_tokens(raw_prompt)
            scene["image_prompt"] = filtered
        return {"scenes": scenes}
    except Exception as exc:
        logger.exception("Storyboard generation failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/scene/generate")
async def generate_scene_image(request: SceneGenerateRequest):
    logger.info("📥 [Scene Gen Req] %s", request.model_dump())
    if not request.prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    cleaned_prompt = normalize_prompt_tokens(request.prompt)
    cleaned_negative = normalize_negative_prompt(request.negative_prompt or "")
    payload = {
        "prompt": cleaned_prompt,
        "negative_prompt": cleaned_negative,
        "steps": request.steps,
        "cfg_scale": request.cfg_scale,
        "sampler_name": request.sampler_name,
        "seed": request.seed,
        "width": request.width,
        "height": request.height,
        "override_settings": {
            "CLIP_stop_at_last_layers": max(1, int(request.clip_skip)),
        },
        "override_settings_restore_afterwards": True,
    }
    if request.enable_hr:
        payload.update({
            "enable_hr": True,
            "hr_scale": request.hr_scale,
            "hr_upscaler": request.hr_upscaler,
            "hr_second_pass_steps": request.hr_second_pass_steps,
            "denoising_strength": request.denoising_strength,
        })
    logger.info("🧾 [Scene Gen Payload] %s", payload)

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(SD_TXT2IMG_URL, json=payload, timeout=SD_TIMEOUT_SECONDS)
            res.raise_for_status()
            data = res.json()
            img = data.get("images", [None])[0]
            if not img:
                raise HTTPException(status_code=500, detail="No image returned")
            return {"image": img}
    except httpx.HTTPError as exc:
        logger.exception("Scene generation failed")
        raise HTTPException(status_code=502, detail=str(exc))


@app.post("/scene/validate_image")
async def validate_scene_image(request: SceneValidateRequest):
    logger.info("📥 [Scene Validate Req] %s", scrub_payload(request.model_dump()))
    try:
        image_bytes = decode_data_url(request.image_b64)
        mode = request.mode.lower().strip() if request.mode else "wd14"
        cache_key = cache_key_for_validation(image_bytes, request.prompt or "", mode)
        cache_file = CACHE_DIR / f"image_validate_{cache_key}.json"
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < CACHE_TTL_SECONDS:
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
                cached["cached"] = True
                return cached
        image = Image.open(io.BytesIO(image_bytes))
        if mode == "gemini":
            tags = gemini_predict_tags(image)
        else:
            tags = wd14_predict_tags(image, WD14_THRESHOLD)
        comparison = compare_prompt_to_tags(request.prompt or "", tags)
        total = len(comparison["matched"]) + len(comparison["missing"])
        match_rate = (len(comparison["matched"]) / total) if total else 0.0
        known_keywords = load_known_keywords()
        unknown_tags = []
        for item in tags[:50]:
            name = normalize_prompt_token(item["tag"])
            if not name:
                continue
            if name not in known_keywords:
                unknown_tags.append(name)
        update_keyword_suggestions(unknown_tags)
        result = {
            "mode": mode,
            "match_rate": match_rate,
            "matched": comparison["matched"],
            "missing": comparison["missing"],
            "extra": comparison["extra"],
            "tags": tags[:20],
            "unknown_tags": unknown_tags[:20],
        }
        cache_file.write_text(json.dumps(result, ensure_ascii=False))
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Scene image validation failed")
        raise HTTPException(status_code=500, detail="Image validation failed") from exc


@app.post("/prompt/rewrite")
async def rewrite_prompt(request: PromptRewriteRequest):
    logger.info("📥 [Prompt Rewrite Req] %s", request.model_dump())
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini key missing")
    if not request.base_prompt or not request.scene_prompt:
        raise HTTPException(status_code=400, detail="Base prompt and scene prompt are required")

    cache_key = hashlib.sha256(
        f"{request.base_prompt}|{request.scene_prompt}|{request.style}|{request.mode}".encode("utf-8")
    ).hexdigest()
    cache_file = CACHE_DIR / f"prompt_{cache_key}.json"
    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < CACHE_TTL_SECONDS:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            return {"prompt": cached.get("prompt", "")}

    if request.mode == "scene":
        instruction = (
            "Convert SCENE into Stable Diffusion tag-style prompt. "
            "Use comma-separated short tags, no full sentences. "
            "Include camera/shot keywords if implied. Return ONLY the tags."
        )
    else:
        instruction = (
            "Rewrite a Stable Diffusion prompt. Keep the identity/style tokens from BASE. "
            "Replace scene/action/camera/background with SCENE. Preserve any <lora:...> tags. "
            "Return ONLY the final comma-separated prompt, no explanations."
        )
    user_input = (
        f"BASE: {request.base_prompt}\n"
        f"SCENE: {request.scene_prompt}\n"
        f"STYLE: {request.style}\n"
    )
    try:
        res = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=f"{instruction}\n\n{user_input}",
        )
        text = res.text.strip().replace("```", "")
        if request.mode == "scene":
            cache_file.write_text(json.dumps({"prompt": text}, ensure_ascii=False))
            return {"prompt": text}
        base_tokens = split_prompt_tokens(request.base_prompt)
        base_core = [
            token for token in base_tokens
            if "<lora:" in token.lower() or not is_scene_token(token)
        ]
        rewritten_tokens = split_prompt_tokens(text)
        final_prompt = merge_prompt_tokens(base_core, rewritten_tokens)
        cache_file.write_text(json.dumps({"prompt": final_prompt}, ensure_ascii=False))
        return {"prompt": final_prompt}
    except Exception as exc:
        logger.exception("Prompt rewrite failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/prompt/split")
async def split_prompt(request: PromptSplitRequest):
    logger.info("📥 [Prompt Split Req] %s", request.model_dump())
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini key missing")
    if not request.example_prompt:
        raise HTTPException(status_code=400, detail="Example prompt is required")

    instruction = (
        "Split the EXAMPLE prompt into BASE and SCENE for Stable Diffusion. "
        "BASE should keep identity/style/LoRA tokens. SCENE should keep action, pose, "
        "camera, and background. Return ONLY JSON with keys base_prompt and scene_prompt."
    )
    user_input = f"EXAMPLE: {request.example_prompt}\nSTYLE: {request.style}\n"
    try:
        res = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=f"{instruction}\n\n{user_input}",
        )
        text = res.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(text)
        return {
            "base_prompt": data.get("base_prompt", ""),
            "scene_prompt": data.get("scene_prompt", ""),
        }
    except Exception as exc:
        logger.exception("Prompt split failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/sd/models")
async def list_sd_models():
    logger.info("📥 [SD Models]")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(SD_MODELS_URL, timeout=10.0)
            res.raise_for_status()
            data = res.json()
            return {"models": data if isinstance(data, list) else []}
    except httpx.HTTPError as exc:
        logger.exception("SD models fetch failed")
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/keywords/suggestions")
async def list_keyword_suggestions(min_count: int = 3, limit: int = 50):
    logger.info("📥 [Keyword Suggestions] min_count=%s limit=%s", min_count, limit)
    suggestions = load_keyword_suggestions(min_count=min_count, limit=limit)
    return {"min_count": min_count, "limit": limit, "suggestions": suggestions}


@app.get("/keywords/categories")
async def list_keyword_categories():
    logger.info("📥 [Keyword Categories]")
    try:
        data = load_keywords_file()
        categories = data.get("categories", {})
        if not isinstance(categories, dict):
            categories = {}
        return {"categories": categories}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Keyword categories load failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/keywords/approve")
async def approve_keyword(request: KeywordApproveRequest):
    logger.info("📥 [Keyword Approve] %s", request.model_dump())
    tag_token = normalize_prompt_token(request.tag)
    if not tag_token:
        raise HTTPException(status_code=400, detail="Invalid tag")
    category = request.category.strip()
    if not category:
        raise HTTPException(status_code=400, detail="Category is required")
    try:
        data = load_keywords_file()
        categories = data.get("categories", {})
        if not isinstance(categories, dict):
            categories = {}
        if category not in categories:
            raise HTTPException(status_code=400, detail="Unknown category")
        entries = categories.get(category) or []
        if not isinstance(entries, list):
            entries = []
        existing = {normalize_prompt_token(item) for item in entries}
        if tag_token not in existing:
            entries.append(tag_token)
        categories[category] = entries
        data["categories"] = categories
        save_keywords_file(data)
        reset_keyword_cache()
        suggestions_path = CACHE_DIR / "keyword_suggestions.json"
        if suggestions_path.exists():
            try:
                suggestions = json.loads(suggestions_path.read_text(encoding="utf-8"))
                if tag_token in suggestions:
                    suggestions.pop(tag_token, None)
                    suggestions_path.write_text(json.dumps(suggestions, ensure_ascii=False, indent=2))
            except Exception:
                logger.exception("Failed to update keyword suggestions after approval")
        return {"ok": True, "tag": tag_token, "category": category}
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Keyword approval failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/sd/options")
async def get_sd_options():
    logger.info("📥 [SD Options]")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(SD_OPTIONS_URL, timeout=10.0)
            res.raise_for_status()
            data = res.json()
            if isinstance(data, dict):
                return {"options": data, "model": data.get("sd_model_checkpoint", "Unknown")}
            return {"options": {}, "model": "Unknown"}
    except httpx.HTTPError as exc:
        logger.exception("SD options fetch failed")
        raise HTTPException(status_code=502, detail=str(exc))


@app.post("/sd/options")
async def update_sd_options(request: SDModelRequest):
    logger.info("📥 [SD Options Update] %s", request.model_dump())
    payload = {"sd_model_checkpoint": request.sd_model_checkpoint}
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(SD_OPTIONS_URL, json=payload, timeout=10.0)
            res.raise_for_status()
            data = res.json()
            return {"ok": True, "model": data.get("sd_model_checkpoint", request.sd_model_checkpoint)}
    except httpx.HTTPError as exc:
        logger.exception("SD options update failed")
        raise HTTPException(status_code=502, detail=str(exc))


@app.post("/video/create")
async def create_video(request: VideoRequest):
    logger.info("📥 [Video Req] %s", scrub_payload(request.model_dump()))
    logger.info("Video build started: %s", request.project_name)

    project_id = f"build_{int(time.time())}"
    temp_dir = IMAGE_DIR / project_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    video_filename = f"{request.project_name}_{int(time.time())}.mp4"
    video_path = VIDEO_DIR / video_filename

    font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
    if not os.path.exists(font_path):
        font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"

    try:
        input_args: list[str] = []
        num_scenes = len(request.scenes)
        speed_multiplier = max(0.25, min(request.speed_multiplier or 1.0, 2.0))
        transition_dur = max(0.1, 0.5 / speed_multiplier)
        tts_padding = 0.5 / speed_multiplier
        tts_rate = to_edge_tts_rate(speed_multiplier)
        tts_valid: list[bool] = []
        tts_durations: list[float] = []

        use_post_layout = request.layout_style == "post"
        for i, scene in enumerate(request.scenes):
            img_path = temp_dir / f"scene_{i}.png"
            tts_path = temp_dir / f"tts_{i}.mp3"
            txt_file = temp_dir / f"text_{i}.txt"

            image_bytes = decode_data_url(scene.image_url)
            if use_post_layout:
                try:
                    overlay_settings = request.overlay_settings or OverlaySettings()
                    composed = compose_post_frame(
                        image_bytes,
                        request.width,
                        request.height,
                        overlay_settings.profile_name,
                        overlay_settings.caption,
                        font_path,
                    )
                    composed.save(img_path, "PNG")
                except Exception:
                    img_path.write_bytes(image_bytes)
            else:
                img_path.write_bytes(image_bytes)

            raw_script = scene.script or ""
            clean_script = re.sub(r"[^\w\s.,!?가-힣a-zA-Zぁ-ゔァ-ヴー々〆〤一-龥]", "", raw_script)
            clean_script = clean_script.replace("'", "").strip()

            if request.include_subtitles:
                wrapped_script = wrap_text(clean_script, width=20)
                txt_file.write_text(wrapped_script, encoding="utf-8")

            has_valid_tts = False
            tts_duration = 0.0
            if raw_script.strip():
                try:
                    voice = request.narrator_voice
                    communicate = edge_tts.Communicate(raw_script, voice, rate=tts_rate)
                    await communicate.save(str(tts_path))
                    if tts_path.exists() and tts_path.stat().st_size > 0:
                        has_valid_tts = True
                        tts_duration = get_audio_duration(tts_path)
                except Exception:
                    pass

            input_args.extend(["-loop", "1", "-i", str(img_path)])
            if has_valid_tts:
                input_args.extend(["-i", str(tts_path)])
            else:
                input_args.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])

            tts_valid.append(has_valid_tts)
            tts_durations.append(tts_duration)

        scene_durations: list[float] = []
        for i, scene in enumerate(request.scenes):
            base_duration = (scene.duration or 3) / speed_multiplier
            if tts_valid[i] and tts_durations[i] > 0:
                base_duration = max(base_duration, tts_durations[i] + tts_padding)
            scene_durations.append(base_duration)

        filters: list[str] = []
        out_w, out_h = (request.width, request.height)
        abs_font_path = str(pathlib.Path(font_path).resolve()).replace("\\", "/")

        for i in range(num_scenes):
            v_idx = i * 2
            base_dur = scene_durations[i]
            clip_dur = base_dur + (transition_dur if i < num_scenes - 1 else 0)
            motion_frames = max(1, int(clip_dur * 25))

            if request.include_subtitles:
                txt_file = temp_dir / f"text_{i}.txt"
                abs_txt_path = str(txt_file.resolve()).replace("\\", "/")

            if use_post_layout:
                if request.motion_style == "slow_zoom":
                    filters.append(
                        f"[{v_idx}:v]scale={out_w}:{out_h},"
                        f"zoompan=z='min(zoom+0.0008,1.08)':d={motion_frames}:s={out_w}x{out_h}:fps=25"
                        f"[v{i}_base]"
                    )
                else:
                    filters.append(f"[{v_idx}:v]scale={out_w}:{out_h}[v{i}_base]")
            else:
                filters.append(f"[{v_idx}:v]split=2[v{i}_in_1][v{i}_in_2]")
                bg_scale = (
                    f"[v{i}_in_1]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
                    f"crop={out_w}:{out_h},boxblur=40:20"
                )
                if request.motion_style == "slow_zoom":
                    filters.append(
                        f"{bg_scale},"
                        f"zoompan=z='min(zoom+0.0008,1.08)':d={motion_frames}:s={out_w}x{out_h}:fps=25"
                        f"[v{i}_bg]"
                    )
                else:
                    filters.append(f"{bg_scale}[v{i}_bg]")

                filters.append(
                    f"[v{i}_in_2]scale={out_w}:-2:force_original_aspect_ratio=decrease[v{i}_fg]"
                )
                filters.append(
                    f"[v{i}_bg][v{i}_fg]overlay=(W-w)/2:(H-h)/2:format=auto[v{i}_base]"
                )

            if request.include_subtitles:
                text_style = "fontcolor=white:fontsize=65:borderw=7:bordercolor=black:shadowx=3:shadowy=3"
                overlay_enabled = bool(request.overlay_settings and request.overlay_settings.enabled)
                if use_post_layout:
                    text_y_pos = str(int(out_h * (0.7 if overlay_enabled else 0.74)))
                else:
                    text_y_pos = str(int(out_h * (0.68 if overlay_enabled else 0.8)))
                filters.append(
                    f"[v{i}_base]drawtext=fontfile='{abs_font_path}':textfile='{abs_txt_path}':"
                    f"{text_style}:x=(w-text_w)/2:y={text_y_pos}[v{i}_text]"
                )
                filters.append(f"[v{i}_text]trim=duration={clip_dur},setpts=PTS-STARTPTS[v{i}_raw]")
            else:
                filters.append(f"[v{i}_base]trim=duration={clip_dur},setpts=PTS-STARTPTS[v{i}_raw]")

        for i in range(num_scenes):
            a_idx = i * 2 + 1
            clip_dur = scene_durations[i] + (transition_dur if i < num_scenes - 1 else 0)
            filters.append(
                f"[{a_idx}:a]aresample=44100,aformat=channel_layouts=stereo,apad,"
                f"atrim=duration={clip_dur},asetpts=PTS-STARTPTS[a{i}_raw]"
            )

        if num_scenes > 1:
            curr_v, curr_a, acc_offset = "[v0_raw]", "[a0_raw]", 0
            for i in range(1, num_scenes):
                prev_dur = scene_durations[i - 1]
                acc_offset += prev_dur
                filters.append(
                    f"{curr_v}[v{i}_raw]xfade=transition=fade:duration={transition_dur}:offset={acc_offset}[v{i}_m]"
                )
                curr_v = f"[v{i}_m]"
                filters.append(
                    f"{curr_a}[a{i}_raw]acrossfade=d={transition_dur}:o=1:c1=tri:c2=tri[a{i}_m]"
                )
                curr_a = f"[a{i}_m]"
            map_v, map_a = curr_v, curr_a
            total_dur = acc_offset + scene_durations[-1]
        else:
            map_v, map_a = "[v0_raw]", "[a0_raw]"
            total_dur = scene_durations[0] if scene_durations else 0

        next_input_idx = num_scenes * 2

        if request.overlay_settings and request.overlay_settings.enabled:
            if request.layout_style == "post":
                logger.info("Overlay disabled for post layout to avoid double UI.")
            else:
                overlay_path = temp_dir / "overlay.png"
                resolve_overlay_frame(request.overlay_settings, out_w, out_h, overlay_path, request.layout_style)
                if request.layout_style == "post":
                    apply_post_overlay_mask(overlay_path, out_w, out_h)
                input_args.extend(["-i", str(overlay_path)])
                if request.layout_style == "full":
                    filters.append(
                        f"[{next_input_idx}:v]scale={out_w}:{out_h},format=rgba,"
                        f"colorchannelmixer=aa=1.6[ovr]"
                    )
                else:
                    filters.append(f"[{next_input_idx}:v]scale={out_w}:{out_h}[ovr]")
                filters.append(f"{map_v}[ovr]overlay=0:0[vid_o]")
                map_v = "[vid_o]"
                next_input_idx += 1

        bgm_path = AUDIO_DIR / request.bgm_file if request.bgm_file else None
        if bgm_path and bgm_path.exists():
            input_args.extend(["-i", str(bgm_path)])
            filters.append(
                f"[{next_input_idx}:a]volume=0.15,afade=t=out:st={max(0, total_dur-2)}:d=2[bgm_f]"
            )
            filters.append(f"{map_a}[bgm_f]amix=inputs=2:duration=first:dropout_transition=2[a_f]")
            map_a = "[a_f]"

        filter_complex_str = ";".join(filters)
        cmd = ["ffmpeg", "-y"] + input_args + [
            "-filter_complex", filter_complex_str,
            "-map", map_v,
            "-map", map_a,
            "-s", f"{out_w}x{out_h}",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "medium",
            "-c:a", "aac",
            "-b:a", "192k",
            str(video_path),
        ]

        logger.info("Running FFmpeg")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("FFmpeg failed: %s", result.stderr)
            raise Exception(result.stderr)

        shutil.rmtree(temp_dir)
        return {"video_url": f"http://localhost:8000/outputs/videos/{video_filename}"}
    except Exception as exc:
        logger.exception("Video Create Error")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise HTTPException(status_code=500, detail=str(exc))


def get_audio_duration(path: pathlib.Path) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return 0.0
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
