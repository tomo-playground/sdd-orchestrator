from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import logging
import os
import pathlib
import random
import re
import shutil
import subprocess
import textwrap
import time
from typing import Any
from urllib.parse import urlparse

import edge_tts
import httpx
import numpy as np
import onnxruntime as ort
from dotenv import load_dotenv
from fastapi import HTTPException
from google import genai
from google.genai import types
from jinja2 import Environment, FileSystemLoader
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

from schemas import (
    OverlaySettings,
    PostCardSettings,
    PromptRewriteRequest,
    PromptSplitRequest,
    SceneGenerateRequest,
    SceneValidateRequest,
    StoryboardRequest,
    VideoRequest,
)

load_dotenv()

# --- Logging ---
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

# --- Configuration & Globals ---
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

for d in (OUTPUT_DIR, IMAGE_DIR, VIDEO_DIR, CANDIDATE_DIR, AVATAR_DIR, CACHE_DIR, AUDIO_DIR, OVERLAY_DIR):
    d.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

BASE_DIR = pathlib.Path(__file__).resolve().parent
template_env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates")))
SD_BASE_URL = os.getenv("SD_BASE_URL", "http://127.0.0.1:7860")
SD_TXT2IMG_URL = f"{SD_BASE_URL}/sdapi/v1/txt2img"
SD_MODELS_URL = f"{SD_BASE_URL}/sdapi/v1/sd-models"
SD_OPTIONS_URL = f"{SD_BASE_URL}/sdapi/v1/options"
SD_LORAS_URL = f"{SD_BASE_URL}/sdapi/v1/loras"
SD_TIMEOUT_SECONDS = float(os.getenv("SD_TIMEOUT_SECONDS", "600"))
API_PUBLIC_URL = os.getenv("API_PUBLIC_URL", "http://localhost:8000").rstrip("/")
WD14_MODEL_DIR = pathlib.Path(os.getenv("WD14_MODEL_DIR", "models/wd14"))
WD14_THRESHOLD = float(os.getenv("WD14_THRESHOLD", "0.35"))

_WD14_SESSION: ort.InferenceSession | None = None
_WD14_TAGS: list[str] | None = None
_WD14_TAG_CATEGORIES: list[str] | None = None
# Keyword functions imported from services
from services.keywords import (
    expand_synonyms,
    filter_prompt_tokens,
    format_keyword_context,
    load_keyword_map,
    load_keyword_suggestions,
    load_keywords_file,
    load_known_keywords,
    normalize_prompt_token,
    reset_keyword_cache,
    save_keywords_file,
    update_keyword_suggestions,
)

# --- Helper Functions ---

def decode_data_url(data_url: str) -> bytes:
    if not data_url:
        raise ValueError("Empty image data")
    b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
    return base64.b64decode(b64)


def load_image_bytes(source: str) -> bytes:
    if not source:
        raise ValueError("Empty image data")
    if source.startswith("data:"):
        return decode_data_url(source)
    if source.startswith(("http://", "https://")):
        parsed = urlparse(source)
        path = parsed.path
    else:
        path = source
    if path.startswith("/outputs/"):
        rel_path = path.replace("/outputs/", "", 1)
        candidate = (OUTPUT_DIR / rel_path).resolve()
        if OUTPUT_DIR.resolve() not in candidate.parents:
            raise ValueError("Invalid image path")
        return candidate.read_bytes()
    raise ValueError("Unsupported image source")


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
    for score, tag, category in zip(preds, tags, categories, strict=False):
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


def wrap_text(text: str, width: int, max_lines: int = 2) -> str:
    if not text:
        return ""
    # "..."을 임시 플레이스홀더로 치환 (split 방지)
    placeholder = "\x00ELLIPSIS\x00"
    text = text.replace("...", placeholder)

    forced_split = None
    for mark in ("…", ".", "!", "?"):
        if mark in text:
            forced_split = mark
            break
    if forced_split:
        head, tail = text.split(forced_split, 1)
        head = head.strip()
        tail = tail.strip()
        if forced_split != "…":
            head = f"{head}{forced_split}"
        lines = [head, tail] if tail else [head]
    else:
        lines = textwrap.wrap(text, width=width)
    if max_lines > 0 and len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines:
            max_tail = max(0, width - 3)
            lines[-1] = lines[-1][:max_tail].rstrip() + "..."

    # 플레이스홀더를 "..."로 복원
    result = "\n".join(lines)
    return result.replace(placeholder, "...")


def avatar_filename(avatar_key: str) -> str:
    safe_name = avatar_key.strip() or "avatar"
    hash_value = hashlib.sha1(safe_name.encode("utf-8")).hexdigest()[:12]
    return f"avatar_{hash_value}.png"


async def ensure_avatar_file(avatar_key: str) -> str | None:
    filename = avatar_filename(avatar_key)
    target = AVATAR_DIR / filename
    if target.exists():
        return filename
    prompt = (
        "anime avatar portrait, clean background, head and shoulders, "
        "soft lighting, centered, high quality"
    )
    payload = {
        "prompt": prompt,
        "negative_prompt": "verybadimagenegative_v1.3",
        "steps": 20,
        "cfg_scale": 7.0,
        "sampler_name": "DPM++ 2M Karras",
        "seed": -1,
        "width": 256,
        "height": 256,
        "override_settings": {"CLIP_stop_at_last_layers": 2},
        "override_settings_restore_afterwards": True,
    }
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(SD_TXT2IMG_URL, json=payload, timeout=60.0)
            res.raise_for_status()
            data = res.json()
        image_b64 = (data.get("images") or [None])[0]
        if not image_b64:
            return None
        image_bytes = base64.b64decode(image_b64)
        target.write_bytes(image_bytes)
        return filename
    except Exception:
        logger.exception("Avatar generation failed")
        return None


def load_avatar_image(filename: str | None) -> Image.Image | None:
    if not filename:
        return None
    candidate = AVATAR_DIR / filename
    if not candidate.exists():
        return None
    try:
        return Image.open(candidate).convert("RGBA")
    except Exception:
        return None


def _seeded_int(value: str) -> int:
    if not value:
        value = "seed"
    return int(hashlib.md5(value.encode("utf-8")).hexdigest(), 16)


def _format_views(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def _clean_caption_title(caption: str) -> str:
    text = re.sub(r"#([^​​#]+)", "", caption or "").strip()
    return re.sub(r"\s{2,}", " ", text).strip()


def _random_meta_values(rng: random.Random) -> tuple[str, str]:
    views_pool = ["1.2k", "2.4k", "3.8k", "5.1k", "7.4k", "9.8k", "12.5k", "18.9k", "24.2k"]
    time_pool = ["방금 전", "1분 전", "2분 전", "5분 전", "10분 전", "30분 전", "1시간 전", "2시간 전"]
    return rng.choice(views_pool), rng.choice(time_pool)


def _build_post_meta(
    channel_name: str,
    caption: str,
    title_text: str,
    views_override: str | None = None,
    time_override: str | None = None,
) -> dict[str, object]:
    seed = _seeded_int(f"{channel_name}|{caption}|{title_text}")
    name_base = (channel_name or "creator").strip()
    suffixes = ["일상", "기록", "로그", "스토리", "채널", "노트"]
    if len(name_base) < 4:
        name_base = f"{name_base}{suffixes[seed % len(suffixes)]}"
    rng = random.Random(seed)
    views, timestamp = _random_meta_values(rng)
    if views_override:
        views = views_override
    if time_override:
        timestamp = time_override
    avatar_palette = [
        (231, 198, 140),
        (210, 232, 192),
        (188, 214, 240),
        (235, 192, 208),
        (206, 196, 235),
        (240, 210, 180),
    ]
    avatar_color = avatar_palette[seed % len(avatar_palette)]
    return {
        "display_name": name_base,
        "timestamp": timestamp,
        "views": views,
        "avatar_color": avatar_color,
    }


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
    font_path = str(ASSETS_DIR / "fonts" / "온글잎 박다현체.ttf")
    if not os.path.exists(font_path):
        font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
        if not os.path.exists(font_path):
            font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
    try:
        return ImageFont.truetype(font_path, size=size)
    except Exception:
        return ImageFont.load_default()


def _get_font_from_path(path: str | None, size: int) -> ImageFont.FreeTypeFont:
    if path and os.path.exists(path):
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            pass
    return _get_font(size)


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


def _emoji_font(size: int) -> ImageFont.FreeTypeFont | None:
    emoji_path = "/System/Library/Fonts/Apple Color Emoji.ttc"
    if not os.path.exists(emoji_path):
        return None
    try:
        return ImageFont.truetype(emoji_path, size=size)
    except Exception:
        return None


def _is_emoji_char(char: str) -> bool:
    return bool(re.match(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]", char))


def resolve_subtitle_font_path(font_name: str | None) -> str:
    default_path = str(ASSETS_DIR / "fonts" / "온글잎 박다현체.ttf")
    if font_name:
        safe_name = os.path.basename(font_name)
        candidate = ASSETS_DIR / "fonts" / safe_name
        if candidate.exists():
            return str(candidate)
    if os.path.exists(default_path):
        return default_path
    return "/System/Library/Fonts/Supplemental/AppleGothic.ttf"


def _measure_text_with_fallback(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    emoji_font: ImageFont.FreeTypeFont | None,
) -> tuple[int, int]:
    total_w = 0
    max_h = 0
    for ch in text:
        active_font = emoji_font if emoji_font and _is_emoji_char(ch) else font
        bbox = draw.textbbox((0, 0), ch, font=active_font)
        ch_w = bbox[2] - bbox[0]
        ch_h = bbox[3] - bbox[1]
        total_w += ch_w
        max_h = max(max_h, ch_h)
    return total_w, max_h


def _draw_text_with_fallback(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    emoji_font: ImageFont.FreeTypeFont | None,
    fill: tuple[int, int, int, int],
    stroke_width: int = 0,
    stroke_fill: tuple[int, int, int, int] = (0, 0, 0, 255),
) -> None:
    cursor_x, cursor_y = xy
    for ch in text:
        active_font = emoji_font if emoji_font and _is_emoji_char(ch) else font
        if stroke_width:
            draw.text(
                (cursor_x, cursor_y),
                ch,
                font=active_font,
                fill=fill,
                stroke_width=stroke_width,
                stroke_fill=stroke_fill,
            )
        else:
            draw.text((cursor_x, cursor_y), ch, font=active_font, fill=fill)
        bbox = draw.textbbox((0, 0), ch, font=active_font)
        cursor_x += bbox[2] - bbox[0]


def render_subtitle_image(
    lines: list[str],
    width: int,
    height: int,
    font_path: str,
    use_post_layout: bool,
    post_layout_metrics: dict[str, int] | None,
) -> Image.Image:
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    if not lines:
        return canvas

    if use_post_layout and post_layout_metrics:
        # 썰/스토리 중심: 자막을 이미지 위 별도 영역에 배치 (겹침 없음)
        # 스토리 중심이므로 가독성 최우선 → 4% 크기
        subtitle_size = int(height * 0.04)
        font = _get_font_from_path(font_path, subtitle_size)
        emoji_font = _emoji_font(subtitle_size)
        line_height = int(subtitle_size * 1.4)
        line_count = len(lines)

        # 자막 영역 정보
        card_x = post_layout_metrics["card_x"]
        card_width = post_layout_metrics["card_width"]
        card_padding = post_layout_metrics["card_padding"]
        subtitle_y = post_layout_metrics["subtitle_y"]
        subtitle_area_height = post_layout_metrics["subtitle_area_height"]

        # 자막 텍스트 (검은색, 중앙 정렬) - 흰색 카드 배경이므로 검은 텍스트
        text_area_width = card_width - (card_padding * 2)
        text_start_y = subtitle_y + int(subtitle_area_height * 0.1)

        for idx, line in enumerate(lines[:3]):
            line_w, _ = _measure_text_with_fallback(draw, line, font, emoji_font)
            text_x = card_x + card_padding + (text_area_width - line_w) // 2
            text_y = text_start_y + idx * line_height
            _draw_text_with_fallback(
                draw,
                (text_x, text_y),
                line,
                font,
                emoji_font,
                (40, 40, 40, 255),  # 검은색 텍스트
            )
        return canvas

    # Full 레이아웃: 이미지 상단 배치 (10%~66%)
    # 자막: 이미지 아래 70% 위치
    subtitle_size = int(height * 0.034)
    font = _get_font_from_path(font_path, subtitle_size)
    emoji_font = _emoji_font(subtitle_size)
    line_height = int(subtitle_size * 1.45)
    line_count = len(lines)

    # 자막 위치: 이미지 아래 (70%)
    if line_count > 1:
        text_y_pos = int(height * 0.70)
    else:
        text_y_pos = int(height * 0.72)

    for idx, line in enumerate(lines[:2]):
        line_w, _ = _measure_text_with_fallback(draw, line, font, emoji_font)
        text_x = max(0, int((width - line_w) / 2))
        _draw_text_with_fallback(
            draw,
            (text_x, text_y_pos + idx * line_height),
            line,
            font,
            emoji_font,
            (255, 255, 255, 255),
            stroke_width=5,
            stroke_fill=(0, 0, 0, 255),
        )
    return canvas


def _draw_common_content(
    draw: ImageDraw.ImageDraw,
    canvas: Image.Image,
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
    show_meta: bool = False,
) -> None:
    avatar_radius = int(header_height * 0.42)  # 80px 직경 (시인성 향상)
    avatar_center = (
        offset_x + safe_margin + avatar_radius + 18,
        offset_y + header_top + header_height // 2,
    )

    avatar_image = load_avatar_image(settings.avatar_file)
    if avatar_image:
        avatar_size = avatar_radius * 2
        avatar_resized = avatar_image.resize((avatar_size, avatar_size), Image.LANCZOS).convert("RGBA")
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        avatar_resized.putalpha(mask)
        canvas.alpha_composite(
            avatar_resized,
            (avatar_center[0] - avatar_radius, avatar_center[1] - avatar_radius),
        )
    else:
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

    name_font = _get_font(int(header_height * 0.34))  # 32px (시인성 향상)
    small_font = _get_font(int(header_height * 0.24))
    caption_font = _get_font(int(footer_height * 0.22))
    avatar_font = _get_font(int(header_height * 0.32))  # 아바타 이니셜

    name_x = avatar_center[0] + avatar_radius + 16
    name_y = offset_y + header_top + int(header_height * 0.18)

    stroke_width = 3 if use_stroke else 0
    stroke_fill = (0, 0, 0, 255)
    meta_line = f"{settings.likes_count} 조회 · 2분 전"
    meta_w = draw.textbbox((0, 0), meta_line, font=small_font)[2]
    meta_x = offset_x + width - safe_margin - meta_w
    meta_y = name_y + int(header_height * 0.5)

    if settings.posted_time:
        meta_line = f"{settings.likes_count} 조회 · {settings.posted_time}"
    if use_stroke:
        _draw_text_with_stroke(
            draw,
            (name_x, name_y),
            settings.channel_name,
            name_font,
            text_color,
            stroke_width,
            stroke_fill,
        )
        if show_meta:
            _draw_text_with_stroke(
                draw,
                (meta_x, meta_y),
                meta_line,
                small_font,
                sub_color,
                stroke_width,
                stroke_fill,
            )
    else:
        draw.text((name_x, name_y), settings.channel_name, fill=text_color, font=name_font)
        if show_meta:
            draw.text((meta_x, meta_y), meta_line, fill=sub_color, font=small_font)

    if not avatar_image:
        initial = (settings.channel_name.strip()[:1] or "A").upper()
        init_w, init_h = draw.textbbox((0, 0), initial, font=avatar_font)[2:]
        draw.text(
            (avatar_center[0] - init_w / 2, avatar_center[1] - init_h / 2),
            initial,
            fill=(30, 30, 30, 255),
            font=avatar_font,
        )

    caption_text = settings.caption or ""
    caption_y = offset_y + footer_top + int(footer_height * 0.2)
    caption_lines: list[str] = []
    if caption_text:
        tokens = caption_text.split()
        emojis = [token for token in tokens if not token.startswith("#")]
        hashtags = [token for token in tokens if token.startswith("#")]
        if emojis:
            caption_lines.append(" ".join(emojis[:6]))
        if hashtags:
            caption_lines.append(" ".join(hashtags[:3]))
    for idx, line in enumerate(caption_lines[:2]):
        y_pos = caption_y + idx * int(footer_height * 0.38)
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
    canvas: Image.Image,
    width: int,
    height: int,
    settings: OverlaySettings,
    offset_x: int = 0,
    offset_y: int = 0,
) -> None:
    # Full 레이아웃: 이미지 상단 배치 (10%~66%)
    # Safe Zone 적용: 헤더 4%~9%, 푸터 80%~90%
    safe_margin = int(width * 0.06)
    header_top = int(height * 0.04)  # 상단 4% (노치 회피)
    header_height = int(height * 0.05)  # 5% 높이 (4%~9%)
    footer_top = int(height * 0.80)  # 80% (하단 여유)
    footer_height = int(height * 0.10)  # 10% 높이 (80%~90%)

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
        canvas,
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
        show_meta=False,
    )


def _draw_minimal_overlay(
    draw: ImageDraw.ImageDraw,
    canvas: Image.Image,
    width: int,
    height: int,
    settings: OverlaySettings,
    offset_x: int = 0,
    offset_y: int = 0,
) -> None:
    # Full 레이아웃: 이미지 상단 배치 (10%~66%)
    # Safe Zone 적용: 헤더 4%~9%, 푸터 80%~90%
    safe_margin = int(width * 0.06)
    header_top = int(height * 0.04)  # 상단 4% (노치 회피)
    header_height = int(height * 0.05)  # 5% 높이 (4%~9%)
    footer_top = int(height * 0.80)  # 80% (하단 여유)
    footer_height = int(height * 0.10)  # 10% 높이 (80%~90%)

    _draw_common_content(
        draw,
        canvas,
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
        show_meta=False,
    )


def _draw_bold_overlay(
    draw: ImageDraw.ImageDraw,
    canvas: Image.Image,
    width: int,
    height: int,
    settings: OverlaySettings,
    offset_x: int = 0,
    offset_y: int = 0,
) -> None:
    # Full 레이아웃: 이미지 상단 배치 (10%~66%)
    # Safe Zone 적용: 헤더 4%~9%, 푸터 80%~90%
    safe_margin = int(width * 0.06)
    header_top = int(height * 0.04)  # 상단 4% (노치 회피)
    header_height = int(height * 0.05)  # 5% 높이 (4%~9%)
    footer_top = int(height * 0.80)  # 80% (하단 여유)
    footer_height = int(height * 0.10)  # 10% 높이 (80%~90%)

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
        canvas,
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
        show_meta=False,
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
        frame_w = int(width * 0.8)
        frame_h = int(height * 0.7)
        offset_x = int(width * 0.05)
        offset_y = (height - frame_h) // 2

    if settings.frame_style == "overlay_minimal.png":
        _draw_minimal_overlay(draw, canvas, frame_w, frame_h, settings, offset_x, offset_y)
    elif settings.frame_style == "overlay_bold.png":
        _draw_bold_overlay(draw, canvas, frame_w, frame_h, settings, offset_x, offset_y)
    else:
        _draw_clean_overlay(draw, canvas, frame_w, frame_h, settings, offset_x, offset_y)

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
    channel_name: str,
    caption: str,
    subtitle_text: str,
    font_path: str,
    avatar_file: str | None = None,
    views_override: str | None = None,
    time_override: str | None = None,
) -> Image.Image:
    """
    썰/스토리 중심 Post 레이아웃 (인스타 포스트 스타일)
    - 헤더: 채널명만 (심플)
    - 자막 영역: 이미지 위 별도 영역 (겹침 없음)
    - 이미지: 깔끔하게 표시
    - 액션바: ♡ 💬 ➤ 🔖
    - 하단: 좋아요 수 + 캡션 + 해시태그 + 시간
    """
    card_offset_y = int(height * 0.04)
    image = Image.open(io.BytesIO(image_bytes))
    image_rgb = image.convert("RGB")
    background = ImageOps.fit(image_rgb, (width, height), Image.LANCZOS)
    background = background.filter(ImageFilter.GaussianBlur(radius=30)).convert("RGBA")
    background.alpha_composite(Image.new("RGBA", (width, height), (0, 0, 0, 20)))

    card_width = int(width * 0.88)
    card_height = int(height * 0.86)
    card_padding = int(card_width * 0.04)
    radius = int(card_width * 0.06)
    header_height = int(card_height * 0.055)  # 심플 헤더 (채널명만)
    subtitle_area_height = int(card_height * 0.18)  # 자막 영역 (3줄 대응)
    action_bar_height = int(card_height * 0.045)  # 액션바
    caption_height = int(card_height * 0.13)  # 캡션 영역
    card = Image.new("RGBA", (card_width, card_height), (255, 255, 255, 245))
    mask = Image.new("L", (card_width, card_height), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, card_width, card_height), radius=radius, fill=255)
    card.putalpha(mask)

    card_x = (width - card_width) // 2
    card_y = max(0, (height - card_height) // 2 + card_offset_y - int(height * 0.05))
    background.alpha_composite(card, (card_x, card_y))

    # 이미지 영역 계산 (헤더, 자막영역, 액션바, 캡션 제외)
    inner_width = card_width - (card_padding * 2)
    inner_height = card_height - (card_padding * 2 + header_height + subtitle_area_height + action_bar_height + caption_height)
    image_area = min(inner_width, inner_height)
    image_area = max(image_area, int(card_width * 0.45))
    image_area = int(image_area * 0.98)
    image_x = card_x + card_padding
    image_y = card_y + card_padding + header_height + subtitle_area_height  # 자막 영역 아래

    inner = ImageOps.fit(image_rgb, (image_area, image_area), Image.LANCZOS).convert("RGBA")
    background.alpha_composite(inner, (image_x, image_y))

    draw = ImageDraw.Draw(background)
    base_post_font = int(height * 0.022)
    name_font_size = base_post_font
    meta_font_size = max(10, int(base_post_font * 0.85))
    caption_font_size = max(10, int(base_post_font * 0.9))
    icon_font_size = max(12, int(base_post_font * 1.2))
    name_font = _get_font_from_path(font_path, name_font_size)
    meta_font = _get_font_from_path(font_path, meta_font_size)
    caption_font = _get_font_from_path(font_path, caption_font_size)

    meta_source = _build_post_meta(
        channel_name,
        caption,
        subtitle_text,
        views_override=views_override,
        time_override=time_override,
    )
    display_name = meta_source["display_name"]
    timestamp = meta_source["timestamp"]
    views = meta_source["views"]
    avatar_color = meta_source["avatar_color"]

    # === 헤더: 아바타 + 채널명만 (심플) ===
    profile_radius = int(card_height * 0.022)
    profile_center = (
        card_x + card_padding + profile_radius,
        card_y + card_padding + int(header_height * 0.5),
    )
    avatar_image = load_avatar_image(avatar_file)
    if avatar_image:
        avatar_size = profile_radius * 2
        avatar_resized = avatar_image.resize((avatar_size, avatar_size), Image.LANCZOS).convert("RGBA")
        avatar_mask = Image.new("L", (avatar_size, avatar_size), 0)
        avatar_mask_draw = ImageDraw.Draw(avatar_mask)
        avatar_mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        avatar_resized.putalpha(avatar_mask)
        background.alpha_composite(
            avatar_resized,
            (profile_center[0] - profile_radius, profile_center[1] - profile_radius),
        )
    else:
        draw.ellipse(
            (
                profile_center[0] - profile_radius,
                profile_center[1] - profile_radius,
                profile_center[0] + profile_radius,
                profile_center[1] + profile_radius,
            ),
            fill=avatar_color,
            outline=(255, 255, 255),
            width=2,
        )
        initial = (str(display_name).strip()[:1] or "A").upper()
        init_font = _get_font_from_path(font_path, int(profile_radius * 1.2))
        text_w, text_h = draw.textbbox((0, 0), initial, font=init_font)[2:]
        draw.text(
            (profile_center[0] - text_w / 2, profile_center[1] - text_h / 2),
            initial,
            fill=(80, 60, 40),
            font=init_font,
        )

    name_x = profile_center[0] + profile_radius + int(card_width * 0.02)
    name_y = profile_center[1] - int(name_font_size * 0.5)
    draw.text((name_x, name_y), display_name, fill=(30, 30, 30), font=name_font)

    # === 액션바: ♡ 💬 ➤    🔖 ===
    action_y = image_y + image_area + int(card_padding * 0.5)
    icon_spacing = int(card_width * 0.08)
    icons_left = ["♡", "💬", "➤"]
    icons_right = ["🔖"]

    icon_x = card_x + card_padding
    for icon in icons_left:
        draw.text((icon_x, action_y), icon, fill=(50, 50, 50), font=meta_font)
        icon_x += icon_spacing

    bookmark_x = card_x + card_width - card_padding - int(icon_spacing * 0.5)
    for icon in icons_right:
        draw.text((bookmark_x, action_y), icon, fill=(50, 50, 50), font=meta_font)

    # === 캡션 영역: 좋아요 + 채널명 + 캡션 + 해시태그 + 시간 ===
    cap_x = card_x + card_padding
    cap_y = action_y + int(action_bar_height * 1.2)

    # 좋아요 수
    likes_text = f"좋아요 {views}개"
    likes_font = _get_font_from_path(font_path, int(meta_font_size * 1.0))
    draw.text((cap_x, cap_y), likes_text, fill=(30, 30, 30), font=likes_font)
    cap_y += int(meta_font_size * 1.8)

    # 채널명 + 캡션
    caption_text = caption.strip()
    hashtags_line = ""
    main_caption = ""
    if caption_text:
        remaining = re.sub(r"#([^\u200b\u200c#]+)", "", caption_text).strip()
        hashtag_matches = re.findall(r"#([^\u200b\u200c#]+)", caption_text)
        if hashtag_matches:
            hashtags_line = " ".join([f"#{tag.strip()}" for tag in hashtag_matches[:4]])
        if remaining:
            main_caption = remaining

    if main_caption:
        caption_line = f"{display_name} {main_caption}"
        max_chars = max(20, int(card_width * 0.08))
        wrapped = textwrap.wrap(caption_line, width=max_chars)[:2]
        for line in wrapped:
            draw.text((cap_x, cap_y), line, fill=(40, 40, 40), font=caption_font)
            cap_y += int(caption_font_size * 1.4)

    # 해시태그
    if hashtags_line:
        draw.text((cap_x, cap_y), hashtags_line, fill=(0, 55, 107), font=meta_font)
        cap_y += int(meta_font_size * 1.6)

    # 게시 시간 (맨 아래)
    time_y = card_y + card_height - card_padding - int(meta_font_size * 1.2)
    draw.text((cap_x, time_y), timestamp, fill=(130, 130, 130), font=meta_font)

    return background.convert("RGB")


def apply_post_overlay_mask(overlay_path: pathlib.Path, width: int, height: int) -> None:
    try:
        overlay = Image.open(overlay_path).convert("RGBA")
    except Exception:
        return

    card_width = int(width * 0.88)
    card_height = int(height * 0.86)
    radius = int(card_width * 0.06)
    card_x = (width - card_width) // 2
    card_y = max(0, (height - card_height) // 2 + int(height * 0.04) - int(height * 0.05))

    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        (card_x, card_y, card_x + card_width, card_y + card_height),
        radius=radius,
        fill=255,
    )
    base_alpha = overlay.getchannel("A")
    non_black = ImageOps.grayscale(overlay.convert("RGB")).point(lambda v: 0 if v < 5 else 255)
    alpha = ImageChops.multiply(base_alpha, non_black)
    overlay.putalpha(ImageChops.multiply(alpha, mask))
    overlay.save(overlay_path, "PNG")


def get_audio_duration(path: pathlib.Path) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return 0.0
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0

# --- Core Business Logic (Moved from Endpoints) ---

def logic_create_storyboard(request: StoryboardRequest) -> dict:
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
        raise HTTPException(status_code=500, detail=str(exc)) from exc

async def logic_generate_scene_image(request: SceneGenerateRequest) -> dict:
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

def logic_validate_scene_image(request: SceneValidateRequest) -> dict:
    try:
        image_bytes = load_image_bytes(request.image_b64)
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

def logic_rewrite_prompt(request: PromptRewriteRequest) -> dict:
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini key missing")
    if not request.base_prompt or not request.scene_prompt:
        raise HTTPException(status_code=400, detail="Base prompt and scene prompt are required")

    cache_key = hashlib.sha256(
        f"{request.base_prompt}|{request.scene_prompt}|{request.style}|{request.mode}".encode()
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
            "Replace scene/action/pose with SCENE. Preserve any <lora:...> tags. "
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

def logic_split_prompt(request: PromptSplitRequest) -> dict:
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

async def logic_create_video(request: VideoRequest) -> dict:
    logger.info("Video build started: %s", request.project_name)

    project_id = f"build_{int(time.time())}"
    temp_dir = IMAGE_DIR / project_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    safe_project_name = re.sub(r"[^​​\w가-힣]+", "_", request.project_name).strip("_")
    if not safe_project_name:
        safe_project_name = "my_shorts"
    safe_project_name = safe_project_name[:40]
    layout_tag = "post" if request.layout_style == "post" else "full"
    timestamp = int(time.time())
    hash_seed = f"{safe_project_name}|{layout_tag}|{timestamp}"
    hash_value = hashlib.sha1(hash_seed.encode("utf-8")).hexdigest()[:12]
    video_filename = f"{safe_project_name}_{layout_tag}_{hash_value}.mp4"
    video_path = VIDEO_DIR / video_filename
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)

    font_path = resolve_subtitle_font_path(request.subtitle_font)

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
        meta_rng = random.Random(time.time_ns())
        full_views, full_time = _random_meta_values(meta_rng)
        post_views, post_time = _random_meta_values(meta_rng)
        avatar_file = None
        if request.overlay_settings:
            request.overlay_settings.likes_count = full_views
            request.overlay_settings.posted_time = full_time
            avatar_file = await ensure_avatar_file(request.overlay_settings.avatar_key)
            if avatar_file:
                request.overlay_settings.avatar_file = avatar_file
        post_avatar_file = None
        if request.post_card_settings:
            post_avatar_file = await ensure_avatar_file(request.post_card_settings.avatar_key)
        subtitle_lines: list[list[str]] = []
        for i, scene in enumerate(request.scenes):
            img_path = temp_dir / f"scene_{i}.png"
            tts_path = temp_dir / f"tts_{i}.mp3"

            image_bytes = load_image_bytes(scene.image_url)
            raw_script = scene.script or ""
            logger.info(f"Scene {i}: script='{raw_script}', len={len(raw_script)}")
            clean_script = re.sub(r"[^​​\w\s.,!?가-힣a-zA-Zぁ-ゔァ-ヴー々〆〤一-龥]", "", raw_script)
            clean_script = clean_script.replace("'", "").strip()
            if use_post_layout:
                try:
                    overlay_settings = request.overlay_settings or OverlaySettings()
                    post_settings = request.post_card_settings or PostCardSettings(
                        channel_name=overlay_settings.channel_name,
                        avatar_key=overlay_settings.avatar_key,
                        caption=overlay_settings.caption,
                    )
                    composed = compose_post_frame(
                        image_bytes, request.width, request.height,
                        post_settings.channel_name, post_settings.caption,
                        "", font_path, post_avatar_file or avatar_file,
                        post_views, post_time,
                    )
                    composed.save(img_path, "PNG")
                except Exception:
                    img_path.write_bytes(image_bytes)
            else:
                img_path.write_bytes(image_bytes)

            if request.include_subtitles:
                wrapped_script = wrap_text(clean_script, width=20, max_lines=2)
                lines = [line for line in wrapped_script.splitlines() if line.strip()]
                subtitle_lines.append(lines)
            else:
                subtitle_lines.append([])

            has_valid_tts = False
            tts_duration = 0.0
            if raw_script.strip():
                try:
                    voice = request.narrator_voice
                    logger.info(f"TTS 생성 시도: voice={voice}, script={raw_script[:50]}...")
                    communicate = edge_tts.Communicate(raw_script, voice, rate=tts_rate)
                    await communicate.save(str(tts_path))
                    if tts_path.exists() and tts_path.stat().st_size > 0:
                        has_valid_tts = True
                        tts_duration = get_audio_duration(tts_path)
                        logger.info(f"TTS 생성 성공: duration={tts_duration}s")
                    else:
                        logger.warning(f"TTS 파일 생성 실패 또는 빈 파일")
                except Exception as e:
                    logger.error(f"TTS 생성 에러: {e}")
            else:
                logger.warning(f"Scene {i}: 스크립트가 비어있어 TTS 생략")

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

        post_layout_metrics = None
        if use_post_layout:
            # 썰/스토리 중심 레이아웃 (compose_post_frame과 동기화)
            card_width = int(out_w * 0.88)
            card_height = int(out_h * 0.86)
            card_padding = int(card_width * 0.04)
            header_height = int(card_height * 0.055)  # 심플 헤더
            subtitle_area_height = int(card_height * 0.18)  # 자막 영역 (3줄 대응)
            action_bar_height = int(card_height * 0.045)  # 액션바
            caption_height = int(card_height * 0.13)  # 캡션 영역
            card_x = (out_w - card_width) // 2
            card_y = max(0, (out_h - card_height) // 2 + int(out_h * 0.04) - int(out_h * 0.05))
            inner_width = card_width - (card_padding * 2)
            inner_height = card_height - (card_padding * 2 + header_height + subtitle_area_height + action_bar_height + caption_height)
            image_area = min(inner_width, inner_height)
            image_area = max(image_area, int(card_width * 0.45))
            image_area = int(image_area * 0.98)
            image_x = card_x + card_padding
            subtitle_y = card_y + card_padding + header_height  # 자막 영역 Y 위치
            image_y = subtitle_y + subtitle_area_height  # 이미지는 자막 아래
            post_layout_metrics = {
                "card_height": card_height,
                "card_padding": card_padding,
                "card_x": card_x,
                "card_y": card_y,
                "card_width": card_width,
                "subtitle_y": subtitle_y,
                "subtitle_area_height": subtitle_area_height,
                "image_x": image_x,
                "image_y": image_y,
                "image_area": image_area,
            }

        subtitle_base_idx = num_scenes * 2
        if request.include_subtitles:
            for i in range(num_scenes):
                subtitle_path = temp_dir / f"subtitle_{i}.png"
                subtitle_img = render_subtitle_image(
                    subtitle_lines[i], out_w, out_h, font_path,
                    use_post_layout, post_layout_metrics,
                )
                subtitle_img.save(subtitle_path, "PNG")
                input_args.extend(["-loop", "1", "-i", str(subtitle_path)])

        for i in range(num_scenes):
            v_idx = i * 2
            base_dur = scene_durations[i]
            clip_dur = base_dur + (transition_dur if i < num_scenes - 1 else 0)
            motion_frames = max(1, int(clip_dur * 25))

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
                # Full 레이아웃: 정사각형 이미지 + 블러 배경
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

                # 정사각형 이미지 (가로 100%, 상단 배치로 영상 강조)
                sq_size = out_w  # 100% 너비
                sq_y = int(out_h * 0.10)  # 상단 10% (헤더 아래)
                filters.append(
                    f"[v{i}_in_2]scale={sq_size}:{sq_size}:force_original_aspect_ratio=decrease,"
                    f"pad={sq_size}:{sq_size}:(ow-iw)/2:(oh-ih)/2[v{i}_sq]"
                )
                filters.append(
                    f"[v{i}_bg][v{i}_sq]overlay=0:{sq_y}:format=auto[v{i}_base]"
                )

            if request.include_subtitles:
                sub_idx = subtitle_base_idx + i
                filters.append(f"[{sub_idx}:v]scale={out_w}:{out_h},format=rgba[sub{i}]")
                filters.append(f"[v{i}_base][sub{i}]overlay=0:0:format=auto[v{i}_text]")
                filters.append(
                    f"[v{i}_text]trim=duration={clip_dur},setpts=PTS-STARTPTS[v{i}_raw]"
                )
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
        if request.include_subtitles:
            next_input_idx += num_scenes

        if request.overlay_settings:
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

        return {"video_url": f"{API_PUBLIC_URL}/outputs/videos/{video_filename}"}
    except Exception as exc:
        logger.exception("Video Create Error")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise HTTPException(status_code=500, detail=str(exc))
