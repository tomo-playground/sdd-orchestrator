from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
from typing import Optional
import httpx
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except Exception:
    NUMPY_AVAILABLE = False
try:
    import cv2
    OPENCV_AVAILABLE = True
except Exception:
    OPENCV_AVAILABLE = False
try:
    import mediapipe as mp
    if hasattr(mp, "solutions"):
        mp_solutions = mp.solutions
        MEDIAPIPE_AVAILABLE = True
    else:
        mp_solutions = None
        MEDIAPIPE_AVAILABLE = False
except Exception:
    mp_solutions = None
    MEDIAPIPE_AVAILABLE = False
try:
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python.vision import FaceDetector, FaceDetectorOptions
    MEDIAPIPE_TASKS_AVAILABLE = True
except Exception:
    MEDIAPIPE_TASKS_AVAILABLE = False
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import time
import os
import hashlib
import pathlib
import json
import base64
import subprocess
import re
import shutil
import textwrap
import io
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from google import genai
from jinja2 import Environment, FileSystemLoader
import edge_tts
from gradio_client import Client as GradioClient
from PIL import Image, ImageDraw, ImageFont

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("backend")

# --- 전역 상수 ---
SD_BASE_URL = os.getenv("SD_BASE_URL", "http://127.0.0.1:7860")
SD_URL = f"{SD_BASE_URL}/sdapi/v1/txt2img"
SD_IMG2IMG_URL = f"{SD_BASE_URL}/sdapi/v1/img2img"
SD_LORA_URL = f"{SD_BASE_URL}/sdapi/v1/loras"
SD_CONFIG_URL = f"{SD_BASE_URL}/sdapi/v1/options"
SD_CONTROLNET_VERSION_URL = f"{SD_BASE_URL}/controlnet/version"
DEFAULT_NEGATIVE_PROMPT = "low quality, worst quality, bad anatomy, deformed, text, watermark, signature, ugly, blurry, out of focus, duplicate, error, artifacts, simplified, cartoon, cgi, render, 3d, (monochrome:1.1), (muted colors:1.2), overexposed, high contrast"

# 디렉토리 설정
CACHE_DIR = pathlib.Path(".cache")
OUTPUT_DIR = pathlib.Path("outputs")
IMAGE_DIR = OUTPUT_DIR / "images"
VIDEO_DIR = OUTPUT_DIR / "videos"
AUDIO_DIR = pathlib.Path("assets/audio")
PROJECTS_DIR = pathlib.Path("projects")
FACE_MODEL_PATH = pathlib.Path("assets/face_detector.tflite")

for d in [CACHE_DIR, IMAGE_DIR, VIDEO_DIR, AUDIO_DIR, PROJECTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Jinja2 설정
template_env = Environment(loader=FileSystemLoader("templates"))

# Gemini 초기화
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = None
if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("✨ [Gemini] 클라이언트 초기화 성공")
    except Exception as e:
        logger.error(f"❌ [Gemini] 초기화 실패: {e}")

# 데이터 모델
class OverlaySettings(BaseModel):
    enabled: bool = False
    profile_name: str = "Daily_Romance"
    likes_count: str = "12.5k"
    caption: str = "설레는 순간들... #럽스타그램"

class CharacterInfo(BaseModel):
    id: int
    role: str
    desc: str
    translatedDesc: str = ""
    voice: str
    seed: int = -1

class GenerateRequest(BaseModel):
    prompt: str
    persona: str | None = None
    lora: list[str] | str | None = None
    negative_prompt: str | None = None
    styles: list[str] = []
    width: int = 512
    height: int = 512
    sampler_name: Optional[str] = "DPM++ 2M Karras" # Better for quality
    cfg_scale: Optional[float] = 7
    seed: int = -1
    steps: int = 30 # Increased for detail
    skip_optimization: bool = False
    reference_image: str | None = None # Base64 string for IP-Adapter
    use_ip_adapter: bool = True

class PortraitRequest(BaseModel):
    description: str
    width: int = 512
    height: int = 512
    styles: list[str] = []

class AnalyzeRequest(BaseModel):
    image: str

class PromptTranslateRequest(BaseModel):
    text: str
    styles: list[str] = []
    persona: str | None = None

class StoryboardRequest(BaseModel):
    topic: str
    duration: int = 30
    style: str = "Cinematic"
    language: str = "Korean"
    structure: str = "Free Flow" # Narrative Pattern
    characters: list[CharacterInfo] = []

class VideoRequest(BaseModel):
    scenes: list[dict]
    project_name: str = "my_shorts"
    bgm_file: str | None = None
    width: int = 1080
    height: int = 1920
    overlay_settings: OverlaySettings | None = None
    characters: list[CharacterInfo] = []
    narrator_voice: str = "ko-KR-SunHiNeural"

class ProjectSaveRequest(BaseModel):
    id: str | None = None
    title: str
    data: dict

class WebUIOptionsUpdateRequest(BaseModel):
    options: Dict[str, Any]

class AudioGenerateRequest(BaseModel):
    prompt: str

class AudioPreviewRequest(BaseModel):
    text: str
    voice: str

class FaceCheckRequest(BaseModel):
    image: str

class WebUIComposeTestRequest(BaseModel):
    prompt: str = "two people sitting in a cafe, cinematic lighting"
    width: int = 512
    height: int = 512
    steps: int = 10
    cfg_scale: float = 6
    denoising_strength: float = 0.6

class DualComposeRequest(BaseModel):
    scene_prompt: str
    char_a_prompt: str
    char_b_prompt: str
    char_a_ref: str | None = None
    char_b_ref: str | None = None
    negative_prompt: str | None = None
    styles: list[str] = []
    lora: list[str] | str | None = None
    width: int = 512
    height: int = 512
    steps: int = 24
    cfg_scale: float = 6
    denoising_strength: float = 0.55
    strict_identity: bool = True
    use_ip_adapter: bool = True

# 유틸리티 함수
def get_audio_duration(path):
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return float(res.stdout.strip())
    except: return 0

def wrap_text(text, width=20):
    return "\n".join(textwrap.wrap(text, width=width))

def strip_data_url(data: str | None) -> str | None:
    if not data:
        return None
    return data.split(",", 1)[1] if "," in data else data

def detect_faces_base64(data: str) -> int:
    raw = strip_data_url(data)
    if not raw:
        return 0
    img_bytes = base64.b64decode(raw)

    if MEDIAPIPE_TASKS_AVAILABLE and NUMPY_AVAILABLE:
        model_path = os.getenv("MEDIAPIPE_FACE_MODEL_PATH")
        if not model_path and FACE_MODEL_PATH.exists():
            model_path = str(FACE_MODEL_PATH)
        if model_path:
            pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            rgb = np.array(pil_img)
            options = FaceDetectorOptions(
                base_options=BaseOptions(model_asset_path=model_path),
                min_detection_confidence=0.4
            )
            detector = FaceDetector.create_from_options(options)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = detector.detect(mp_image)
            return len(result.detections) if result.detections else 0

    if MEDIAPIPE_AVAILABLE and mp_solutions is not None:
        img_arr = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR) if OPENCV_AVAILABLE else None
        if img is None:
            pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            img = np.array(pil_img)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) if OPENCV_AVAILABLE else img
        with mp_solutions.face_detection.FaceDetection(
            model_selection=0,
            min_detection_confidence=0.4
        ) as detector:
            results = detector.process(rgb)
            return len(results.detections) if results.detections else 0

    if not OPENCV_AVAILABLE:
        raise RuntimeError("Face detection not available")

    img_arr = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
    if img is None:
        return 0
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    def _detect(gray, min_neighbors=4, min_size=(30, 30)):
        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=min_neighbors,
            minSize=min_size
        )
        return len(faces)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    count = _detect(gray, min_neighbors=4, min_size=(30, 30))
    if count > 0:
        return count

    # Retry on resized image to help small/low-res faces
    h, w = gray.shape[:2]
    scale = 1024 / max(h, w)
    if scale > 1.0:
        resized = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
        count = _detect(resized, min_neighbors=3, min_size=(24, 24))
        if count > 0:
            return count

    # Retry on central crop (often the face is centered)
    crop_size = int(min(h, w) * 0.7)
    if crop_size >= 64:
        y0 = (h - crop_size) // 2
        x0 = (w - crop_size) // 2
        crop = gray[y0:y0 + crop_size, x0:x0 + crop_size]
        count = _detect(crop, min_neighbors=3, min_size=(24, 24))
        if count > 0:
            return count

    # Last attempt: lighten normalization
    eq = cv2.equalizeHist(gray)
    count = _detect(eq, min_neighbors=3, min_size=(24, 24))
    return count

def image_to_base64(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")

def build_prompt(base: str, styles: list[str], lora: list[str] | str | None) -> str:
    parts = [base.strip()]
    if styles:
        parts.append(", ".join(styles))
    prompt = ", ".join([p for p in parts if p])
    if lora:
        if isinstance(lora, list):
            for item in lora:
                if item:
                    prompt = f"{prompt}, <lora:{item}:1>"
        else:
            prompt = f"{prompt}, <lora:{lora}:1>"
    return prompt

def build_person_mask(width: int, height: int, side: str) -> str:
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    cx = int(width * (0.33 if side == "left" else 0.67))
    cy = int(height * 0.6)
    rx = int(width * 0.22)
    ry = int(height * 0.32)
    draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
    return image_to_base64(mask)

def build_face_mask(width: int, height: int, side: str) -> str:
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    cx = int(width * (0.33 if side == "left" else 0.67))
    cy = int(height * 0.38)
    r = int(min(width, height) * 0.08)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    return image_to_base64(mask)

def build_pose_guide(width: int, height: int, side: str) -> str:
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    cx = int(width * (0.33 if side == "left" else 0.67))
    cy = int(height * 0.55)
    head_r = int(min(width, height) * 0.05)
    body_len = int(height * 0.18)
    arm_len = int(width * 0.12)
    leg_len = int(height * 0.18)
    line_w = max(3, width // 128)

    draw.ellipse([cx - head_r, cy - body_len - head_r * 2, cx + head_r, cy - body_len], outline=(0, 0, 0), width=line_w)
    draw.line([cx, cy - body_len, cx, cy + body_len // 2], fill=(0, 0, 0), width=line_w)
    draw.line([cx - arm_len, cy - body_len // 2, cx + arm_len, cy - body_len // 2], fill=(0, 0, 0), width=line_w)
    draw.line([cx, cy + body_len // 2, cx - arm_len // 2, cy + body_len // 2 + leg_len], fill=(0, 0, 0), width=line_w)
    draw.line([cx, cy + body_len // 2, cx + arm_len // 2, cy + body_len // 2 + leg_len], fill=(0, 0, 0), width=line_w)
    return image_to_base64(img)

def mask_blur_for_size(width: int, height: int) -> int:
    base = min(width, height)
    return max(4, min(18, base // 64))

def adetailer_args_for_size(width: int, height: int, prompt: str) -> dict:
    return {
        "ad_model": "face_yolov8n.pt",
        "ad_prompt": prompt,
        "ad_negative_prompt": "",
        "ad_confidence": 0.3,
        "ad_mask_blur": 4,
        "ad_inpaint_only_masked": True,
        "ad_inpaint_only_masked_padding": 32,
        "ad_use_inpaint_width_height": True,
        "ad_inpaint_width": min(512, width),
        "ad_inpaint_height": min(512, height)
    }

# Dynamic Overlay Generator
def create_dynamic_overlay(settings: OverlaySettings, output_path: pathlib.Path, width: int = 1080, height: int = 1920):
    W, H = width, height
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    ui_bg_color = (255, 255, 255, 255)
    text_color = (38, 38, 38, 255)
    
    # --- Font Loading Strategy ---
    font_candidates = [
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/Library/Fonts/AppleGothic.ttf",
        "arial.ttf"
    ]
    
    font_large = font_medium = font_small = None
    for f_path in font_candidates:
        if os.path.exists(f_path) or f_path == "arial.ttf":
            try:
                font_large = ImageFont.truetype(f_path, 40, index=0)
                font_medium = ImageFont.truetype(f_path, 35, index=0)
                font_small = ImageFont.truetype(f_path, 28, index=0)
                break
            except: continue
    
    if font_large is None:
        font_large = font_medium = font_small = ImageFont.load_default()

    # --- Responsive Layout Calculation ---
    # Base reference is 1080x1920.
    # We want fixed height bars for 1920, but scale down if H is small.
    # Header 160px, Footer 390px (incl icons). Total 550px.
    # If H < 600 (e.g. 512), 550 > 512 -> Overlap.
    
    scale = 1.0
    target_header_h = 160
    target_footer_h = 390
    
    # Check if we need to shrink
    if H < (target_header_h + target_footer_h + 100): # Ensure at least 100px content
        available_h = H - 100
        required_h = target_header_h + target_footer_h
        scale = available_h / required_h
        scale = max(0.3, scale) # Don't shrink to invisible
    
    header_h = int(target_header_h * scale)
    footer_h = int(target_footer_h * scale)
    footer_y = H - footer_h
    
    # Header
    draw.rectangle([(0, 0), (W, header_h)], fill=ui_bg_color)
    
    # Profile
    profile_r = int(45 * scale)
    profile_cx = int(80 * scale) 
    profile_cy = header_h // 2
    
    if header_h > 40:
        draw.ellipse([(profile_cx-profile_r, profile_cy-profile_r), (profile_cx+profile_r, profile_cy+profile_r)], fill=(220, 220, 220, 255))
        
        # Text Logic (approximate positions scaled)
        text_x = int(150 * scale)
        name_y = int(55 * scale)
        sub_y = int(105 * scale)
        
        # Use scaled font if possible, but load_default doesn't scale. 
        # Ideally we reload fonts, but for now we assume standard fonts.
        draw.text((text_x, name_y), settings.profile_name, fill=text_color, font=font_large)
        draw.text((text_x, sub_y), "Sponsored", fill=(150, 150, 150, 255), font=font_small)
        
        dot_r = int(4 * scale)
        dot_y = profile_cy
        for i in range(3):
            dx = int((980 + (i * 15)) * scale) # This assumes 1080 width logic, might be off for 512 width
            # Fix X positioning relative to Right edge
            dx = W - int((100 - (i*15)) * scale) 
            draw.ellipse([(dx-dot_r, dot_y-dot_r), (dx+dot_r, dot_y+dot_r)], fill=text_color)

    # Footer
    draw.rectangle([(0, footer_y), (W, H)], fill=ui_bg_color)
    icon_y = footer_y + int(60 * scale)
    
    if footer_h > 50:
        # Icons (Relative to Left)
        icons_scale = scale
        
        # Heart
        cx, cy = int(80 * icons_scale), icon_y + int(25 * icons_scale)
        r = int(20 * icons_scale)
        draw.ellipse([(cx-r, cy-r), (cx+r, cy+r)], fill=(255, 60, 60, 255))
        
        # Comment
        c_x = int(180 * icons_scale)
        draw.ellipse([(c_x, icon_y), (c_x + int(40*scale), icon_y + int(35*scale))], outline=text_color, width=3)
        
        # Share
        s_x = int(300 * icons_scale)
        # Simplified polygon scaling is hard, just drawing a box or skipping for simplicity if too small
        if scale > 0.5:
             draw.rectangle([(s_x, icon_y), (s_x + 30, icon_y + 30)], outline=text_color, width=3)

        # Bookmark (Right aligned)
        b_x = W - int(120 * scale)
        draw.rectangle([(b_x, icon_y), (b_x + 30, icon_y + 40)], outline=text_color, width=3)

        # Text Info
        info_y = icon_y + int(100 * scale)
        draw.text((int(60*scale), info_y), f"좋아요 {settings.likes_count}", fill=text_color, font=font_medium)
        
        caption_y = icon_y + int(160 * scale)
        draw.text((int(60*scale), caption_y), settings.profile_name, fill=text_color, font=font_medium)
        draw.text((int(60*scale) + 150, caption_y), settings.caption, fill=(80, 80, 80, 255), font=font_medium)

    img.save(output_path)

# --- FastAPI 앱 설정 ---
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/outputs/videos/")
async def list_videos_directory_handler():
    return {"message": "Directory listing disabled, use /video/list"}

app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

@app.get("/loras")
async def get_loras():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(SD_LORA_URL, timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict): data = data.get("loras", [])
                if isinstance(data, list):
                    loras = []
                    for item in data:
                        if isinstance(item, dict):
                            name = item.get("name") or item.get("alias")
                            if name: loras.append(name)
                        elif isinstance(item, str): loras.append(item)
                    return {"loras": sorted(list(set(loras)))}
            return {"loras": []}
    except: return {"loras": []}

@app.get("/config")
async def get_config():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(SD_CONFIG_URL, timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict): return {"model": data.get("sd_model_checkpoint", "Unknown")}
            return {"model": "Offline"}
    except: return {"model": "Offline"}

@app.get("/debug/webui/options")
async def get_webui_options():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(SD_CONFIG_URL, timeout=5.0)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict):
                return {"options": data}
            return {"options": {}}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.post("/debug/webui/options")
async def update_webui_options(request: WebUIOptionsUpdateRequest):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(SD_CONFIG_URL, json=request.options, timeout=5.0)
            r.raise_for_status()
            data = r.json()
            return {"ok": True, "options": data if isinstance(data, dict) else request.options}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/debug/webui/controlnet")
async def get_controlnet_status():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(SD_CONTROLNET_VERSION_URL, timeout=5.0)
            r.raise_for_status()
            data = r.json()
            return {"controlnet": data if isinstance(data, dict) else {}}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/audio/list")
async def get_audio_list():
    try:
        files = []
        for ext in ["*.mp3", "*.MP3", "*.wav", "*.WAV", "*.m4a", "*.M4A"]:
            for f in AUDIO_DIR.glob(ext):
                files.append({"name": f.name, "url": f"http://localhost:8000/assets/audio/{f.name}"})
        return {"audios": sorted(files, key=lambda x: x["name"])}
    except: return {"audios": []}

@app.post("/projects/save")
async def save_project(request: ProjectSaveRequest):
    project_id = request.id or f"proj_{int(time.time())}"
    file_path = PROJECTS_DIR / f"{project_id}.json"
    project_data = {"id": project_id, "title": request.title, "updated_at": time.time(), "content": request.data}
    file_path.write_text(json.dumps(project_data, ensure_ascii=False, indent=2))
    return project_data

@app.get("/projects/list")
async def list_projects():
    projects = []
    for f in PROJECTS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            projects.append({"id": data["id"], "title": data["title"], "updated_at": data["updated_at"]})
        except: continue
    projects.sort(key=lambda x: x["updated_at"], reverse=True)
    return {"projects": projects}

@app.get("/projects/{project_id}")
async def load_project(project_id: str):
    file_path = PROJECTS_DIR / f"{project_id}.json"
    if not file_path.exists(): raise HTTPException(status_code=404)
    return json.loads(file_path.read_text())

@app.get("/video/list")
async def get_video_list():
    videos = []
    for f in VIDEO_DIR.glob("*.mp4"):
        videos.append({"name": f.name, "url": f"http://localhost:8000/outputs/videos/{f.name}", "created_at": f.stat().st_mtime})
    videos.sort(key=lambda x: x["created_at"], reverse=True)
    return {"videos": videos}

@app.delete("/video/{filename}")
async def delete_video(filename: str):
    file_path = VIDEO_DIR / filename
    if file_path.exists(): file_path.unlink(); return {"status": "success"}
    raise HTTPException(status_code=404)

@app.get("/random-prompt")
async def get_random_prompt():
    if not gemini_client: return {"prompt": "신비로운 숲속의 고양이"}
    try:
        res = gemini_client.models.generate_content(model="gemini-2.0-flash-exp", contents="Generate one creative visual description in Korean.")
        return {"prompt": res.text.strip()}
    except: return {"prompt": "미래 도시의 네온사인"}

@app.post("/audio/preview")
async def preview_audio(request: AudioPreviewRequest):
    try:
        h = hashlib.md5(f"{request.text}{request.voice}".encode()).hexdigest()
        filename = f"preview_{h}.mp3"
        preview_path = OUTPUT_DIR / filename
        if not preview_path.exists(): await edge_tts.Communicate(request.text, request.voice).save(str(preview_path))
        return {"url": f"http://localhost:8000/outputs/{filename}"}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/audio/generate")
async def generate_audio(request: AudioGenerateRequest):
    try:
        client = GradioClient("facebook/MusicGen")
        result = client.predict(task="text-to-audio", text=request.prompt, model_name="facebook/musicgen-small", api_name="/predict")
        filename = f"ai_bgm_{int(time.time())}.mp3"
        shutil.copy(result, AUDIO_DIR / filename)
        return {"filename": filename}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

class OverlayGenRequest(BaseModel):
    topic: str

# ... (Previous code) ...

@app.post("/overlay/generate")
async def generate_overlay_data(request: OverlayGenRequest):
    if not gemini_client: return {
        "profile_name": "daily_shorts", "likes_count": "12.5k", "caption": "Amazing video! #viral #shorts"
    }
    try:
        prompt = f"""
        Generate viral social media (TikTok/Reels) metadata for a video about: "{request.topic}".
        Return ONLY a JSON object with these keys:
        - profile_name: A catchy username (e.g. travel_w_me)
        - likes_count: A realistic number (e.g. 14.2k, 1.2M)
        - caption: A short, engaging caption (max 50 chars) with 2-3 hashtags.
        """
        res = gemini_client.models.generate_content(model="gemini-2.0-flash-exp", contents=prompt)
        return json.loads(res.text.strip().replace("```json", "").replace("```", ""))
    except Exception as e:
        logger.error(f"Overlay Gen Failed: {e}")
        return {"profile_name": "story_teller", "likes_count": "5.2k", "caption": "Check this out! #trending"}

@app.post("/character/analyze")
async def analyze_character(request: AnalyzeRequest):
    if not gemini_client: raise HTTPException(status_code=503, detail="Gemini key missing")
    try:
        # Base64 to Image
        img_data = request.image.split(",")[1] if "," in request.image else request.image
        image = Image.open(io.BytesIO(base64.b64decode(img_data)))
        
        prompt = "Analyze this character's visual appearance in detail (hair, eyes, clothing, age, gender, vibe). Write a concise description (max 2 sentences) in Korean."
        res = gemini_client.models.generate_content(model="gemini-2.0-flash-exp", contents=[prompt, image])
        return {"description": res.text.strip()}
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/prompt/translate")
async def translate_prompt(request: PromptTranslateRequest):
    if not gemini_client:
        return {"translated_prompt": request.text, "negative_prompt": DEFAULT_NEGATIVE_PROMPT}
    try:
        template = template_env.get_template("optimize_prompt.j2")
        rendered = template.render(user_input=request.text, persona=request.persona, target_styles=", ".join(request.styles))
        h = hashlib.sha256(rendered.encode()).hexdigest()
        cache_file = CACHE_DIR / f"{h}.json"
        
        if cache_file.exists():
            res_json = json.loads(cache_file.read_text(encoding="utf-8"))
        else:
            res = gemini_client.models.generate_content(model="gemini-2.0-flash-exp", contents=rendered)
            res_json = json.loads(res.text.strip().replace("```json", "").replace("```", ""))
            cache_file.write_text(json.dumps(res_json, ensure_ascii=False))
            
        return {
            "translated_prompt": res_json.get("positive_prompt", request.text), 
            "negative_prompt": res_json.get("negative_prompt", DEFAULT_NEGATIVE_PROMPT)
        }
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return {"translated_prompt": request.text, "negative_prompt": DEFAULT_NEGATIVE_PROMPT}

@app.post("/face/check")
async def face_check(request: FaceCheckRequest):
    if not OPENCV_AVAILABLE and not MEDIAPIPE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Face detection unavailable. Install mediapipe or opencv-python.")
    try:
        logger.info("🧪 [Face Check] Started (mediapipe=%s, opencv=%s)", MEDIAPIPE_AVAILABLE, OPENCV_AVAILABLE)
        faces = detect_faces_base64(request.image)
        logger.info("🧪 [Face Check] Detected faces: %s", faces)
        return {"has_face": faces > 0, "faces": faces}
    except Exception as e:
        logger.exception("Face check failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/character/portrait")
async def generate_portrait(request: PortraitRequest):
    """Generates a high-quality reference portrait for a character."""
    
    style_prompt = ", ".join(request.styles)
    final_prompt = request.description
    
    # 1. Optimize/Translate Prompt with Gemini if available
    if gemini_client:
        try:
            prompt_instruction = f"""
            You are a Stable Diffusion Prompt Expert.
            Convert this character description into a detailed, comma-separated English prompt for a high-quality portrait.
            The user also wants these styles: "{style_prompt}".
            Focus on: Gender, Age, Hair, Eyes, Facial features, Atmosphere, and the requested Art Style.
            Input: "{request.description}"
            Output example: "Anime style, flat color, A handsome young boy, 7 years old, orange messy hair, blue eyes"
            Return ONLY the prompt string.
            """
            res = gemini_client.models.generate_content(model="gemini-2.0-flash-exp", contents=prompt_instruction)
            final_prompt = res.text.strip()
        except Exception as e:
            logger.warning(f"Portrait Prompt Optimization Failed: {e}")

    # Construct final prompt with face-detection-friendly constraints
    prompt = (
        f"(({final_prompt})), portrait, close-up headshot, centered composition, single person, "
        "front-facing, face fully visible, eyes visible, no occlusion, looking at camera, "
        "neutral expression, clean background, professional lighting, highly detailed"
    )
    logger.info(f"📸 [Portrait Gen] Prompt: {prompt}")
    
    payload = {
        "prompt": prompt,
        "negative_prompt": (
            "low quality, blurry, distorted face, extra limbs, multiple people, "
            "profile, side view, occluded face, mask, sunglasses, hat, "
            "(nsfw:1.5), (worst quality, low quality:1.4)"
        ),
        "steps": 30,
        "width": request.width,
        "height": request.height,
        "sampler_name": "DPM++ 2M Karras",
        "cfg_scale": 7,
        "seed": -1
    }
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(SD_URL, json=payload, timeout=120.0)
            r.raise_for_status()
            data = r.json()
            return {"image": data.get("images", [])[0]}
        except Exception as e:
            logger.error(f"Portrait Gen Failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate")
async def generate_image(request: GenerateRequest):
    logger.info(f"🎨 [Image Gen] Prompt: {request.prompt[:50]}...")
    final_pos, final_neg = request.prompt, request.negative_prompt or DEFAULT_NEGATIVE_PROMPT
    
    if gemini_client and not request.skip_optimization:
        try:
            template = template_env.get_template("optimize_prompt.j2")
            rendered = template.render(user_input=request.prompt, persona=request.persona, target_styles=", ".join(request.styles))
            h = hashlib.sha256(rendered.encode()).hexdigest()
            cache_file = CACHE_DIR / f"{h}.json"
            if cache_file.exists():
                res_json = json.loads(cache_file.read_text(encoding="utf-8"))
            else:
                res = gemini_client.models.generate_content(model="gemini-2.0-flash-exp", contents=rendered)
                res_json = json.loads(res.text.strip().replace("```json", "").replace("```", ""))
                cache_file.write_text(json.dumps(res_json, ensure_ascii=False))
            final_pos, final_neg = res_json.get("positive_prompt", final_pos), res_json.get("negative_prompt", final_neg)
        except Exception as e:
            logger.warning(f"⚠️ Prompt Optimization Failed: {e}")
    
    payload = {
        "prompt": build_prompt(final_pos, [], request.lora),
        "negative_prompt": final_neg,
        "steps": request.steps,
        "width": request.width,
        "height": request.height,
        "sampler_name": request.sampler_name,
        "cfg_scale": request.cfg_scale,
        "seed": request.seed,
        "alwayson_scripts": {}
    }

    # ControlNet / IP-Adapter Injection
    if request.reference_image and request.use_ip_adapter:
        logger.info("🔗 IP-Adapter Activated with reference image")
        # Ensure clean base64
        ref_img_clean = request.reference_image.split(",")[1] if "," in request.reference_image else request.reference_image
        
        payload["alwayson_scripts"]["controlnet"] = {
            "args": [
                {
                    "enabled": True,
                    "module": "ip-adapter_face_id_plus",
                    "model": "ip-adapter-faceid-plusv2_sd15 [6e14fc1a]",
                    "weight": 0.8,
                    "image": ref_img_clean,
                    "pixel_perfect": True
                }
            ]
        }
    
    async with httpx.AsyncClient() as client:
        try:
            logger.info("📡 Sending request to SD WebUI...")
            r = await client.post(SD_URL, json=payload, timeout=120.0)
            r.raise_for_status()
            logger.info("✅ SD WebUI Response Received")
            
            data = r.json()
            info = json.loads(data.get("info", "{}"))
            return {"images": data.get("images", []), "seed": info.get("seed", request.seed), "translated_prompt": final_pos, "negative_prompt": final_neg}
        except httpx.HTTPStatusError as e:
            err_text = e.response.text if e.response is not None else ""
            if "Insightface: No face found" in err_text and payload.get("alwayson_scripts", {}).get("controlnet"):
                logger.warning("⚠️ No face found in reference image. Retrying without IP-Adapter...")
                payload["alwayson_scripts"]["controlnet"]["args"] = [
                    arg for arg in payload["alwayson_scripts"]["controlnet"]["args"]
                    if arg.get("module") != "ip-adapter_face_id_plus"
                ]
                r = await client.post(SD_URL, json=payload, timeout=120.0)
                r.raise_for_status()
                data = r.json()
                info = json.loads(data.get("info", "{}"))
                return {"images": data.get("images", []), "seed": info.get("seed", request.seed), "translated_prompt": final_pos, "negative_prompt": final_neg}
            logger.error(f"❌ Image Generation Failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.error(f"❌ Image Generation Failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate/compose_dual")
async def generate_compose_dual(request: DualComposeRequest):
    final_neg = request.negative_prompt or DEFAULT_NEGATIVE_PROMPT
    char_a_ref = strip_data_url(request.char_a_ref)
    char_b_ref = strip_data_url(request.char_b_ref)

    base_prompt = f"{request.scene_prompt}, background, empty scene, no people"
    base_prompt = build_prompt(base_prompt, request.styles, request.lora)
    cache_key = hashlib.sha256(
        json.dumps(
            {
                "prompt": base_prompt,
                "width": request.width,
                "height": request.height,
                "steps": request.steps,
                "cfg_scale": request.cfg_scale
            },
            sort_keys=True
        ).encode()
    ).hexdigest()
    cache_file = CACHE_DIR / f"bg_{cache_key}.json"

    txt2img_payload = {
        "prompt": base_prompt,
        "negative_prompt": final_neg,
        "steps": request.steps,
        "width": request.width,
        "height": request.height,
        "sampler_name": "DPM++ 2M Karras",
        "cfg_scale": request.cfg_scale,
        "seed": -1
    }

    async with httpx.AsyncClient() as client:
        try:
            logger.info("🧩 [Compose Dual] Generating background...")
            if cache_file.exists():
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
                current_b64 = cached.get("image")
            else:
                r = await client.post(SD_URL, json=txt2img_payload, timeout=120.0)
                r.raise_for_status()
                data = r.json()
                current_b64 = data.get("images", [None])[0]
                if current_b64:
                    cache_file.write_text(json.dumps({"image": current_b64}), encoding="utf-8")
            if not current_b64:
                raise HTTPException(status_code=500, detail="Background generation failed")

            for side, char_prompt, ref_image in [
                ("left", request.char_a_prompt, char_a_ref),
                ("right", request.char_b_prompt, char_b_ref),
            ]:
                if request.use_ip_adapter and not ref_image:
                    raise HTTPException(status_code=400, detail=f"Missing reference image for {side} character")
                mask_b64 = build_person_mask(request.width, request.height, side)
                pose_b64 = build_pose_guide(request.width, request.height, side)
                mask_blur = mask_blur_for_size(request.width, request.height)
                person_prompt = f"{request.scene_prompt}, {char_prompt}, {side} side, full body"
                person_prompt = build_prompt(person_prompt, request.styles, request.lora)

                controlnet_args = [
                    {
                        "enabled": True,
                        "module": "openpose_full",
                        "model": "control_v11p_sd15_openpose [cab727d4]",
                        "weight": 0.5,
                        "image": pose_b64,
                        "pixel_perfect": True
                    },
                    {
                        "enabled": True,
                        "module": "depth",
                        "model": "control_v11f1p_sd15_depth [cfd03158]",
                        "weight": 0.4,
                        "image": current_b64,
                        "pixel_perfect": True
                    },
                    {
                        "enabled": True,
                        "module": "inpaint",
                        "model": "control_v11p_sd15_inpaint [ebff9138]",
                        "weight": 0.8,
                        "image": current_b64,
                        "mask": mask_b64,
                        "pixel_perfect": True
                    }
                ]
                if ref_image and request.use_ip_adapter:
                    controlnet_args.append(
                        {
                            "enabled": True,
                            "module": "ip-adapter_face_id_plus",
                            "model": "ip-adapter-faceid-plusv2_sd15 [6e14fc1a]",
                            "weight": 0.9,
                            "image": ref_image,
                            "pixel_perfect": True
                        }
                    )

                img2img_payload = {
                    "prompt": person_prompt,
                    "negative_prompt": final_neg,
                    "steps": request.steps,
                    "width": request.width,
                    "height": request.height,
                    "sampler_name": "DPM++ 2M Karras",
                    "cfg_scale": request.cfg_scale,
                    "seed": -1,
                    "init_images": [current_b64],
                    "mask": mask_b64,
                    "mask_blur": mask_blur,
                    "inpainting_fill": 1,
                    "inpaint_full_res": True,
                    "inpaint_full_res_padding": 32,
                    "denoising_strength": request.denoising_strength,
                    "alwayson_scripts": {
                        "controlnet": {"args": controlnet_args},
                        "adetailer": {"args": [adetailer_args_for_size(request.width, request.height, char_prompt)]}
                    }
                }

                logger.info("🧩 [Compose Dual] Inpainting %s character...", side)
                try:
                    r = await client.post(SD_IMG2IMG_URL, json=img2img_payload, timeout=120.0)
                    r.raise_for_status()
                    data = r.json()
                except httpx.HTTPStatusError as e:
                    err_text = e.response.text if e.response is not None else ""
                    if "Insightface: No face found" in err_text and request.use_ip_adapter:
                        if request.strict_identity:
                            raise HTTPException(
                                status_code=400,
                                detail="Reference image must contain a clear face for identity locking."
                            )
                        logger.warning("⚠️ No face found in reference image. Retrying without IP-Adapter...")
                        img2img_payload["alwayson_scripts"]["controlnet"]["args"] = [
                            arg for arg in controlnet_args if arg.get("module") != "ip-adapter_face_id_plus"
                        ]
                    logger.warning("⚠️ Retrying without ADetailer...")
                    img2img_payload["alwayson_scripts"].pop("adetailer", None)
                    r = await client.post(SD_IMG2IMG_URL, json=img2img_payload, timeout=120.0)
                    r.raise_for_status()
                    data = r.json()
                current_b64 = data.get("images", [None])[0]
                if not current_b64:
                    raise HTTPException(status_code=500, detail=f"{side} character inpaint failed")

                face_mask_b64 = build_face_mask(request.width, request.height, side)
                face_prompt = f"{char_prompt}, face, same person, high fidelity"
                face_prompt = build_prompt(face_prompt, request.styles, request.lora)
                face_payload = {
                    "prompt": face_prompt,
                    "negative_prompt": final_neg,
                    "steps": max(12, request.steps // 2),
                    "width": request.width,
                    "height": request.height,
                    "sampler_name": "DPM++ 2M Karras",
                    "cfg_scale": max(4.5, request.cfg_scale - 1),
                    "seed": -1,
                    "init_images": [current_b64],
                    "mask": face_mask_b64,
                    "mask_blur": max(2, mask_blur // 2),
                    "inpainting_fill": 1,
                    "inpaint_full_res": True,
                    "inpaint_full_res_padding": 16,
                    "denoising_strength": min(0.4, request.denoising_strength),
                    "alwayson_scripts": {
                        "controlnet": {
                            "args": [
                                {
                                    "enabled": True,
                                    "module": "ip-adapter_face_id_plus",
                                    "model": "ip-adapter-faceid-plusv2_sd15 [6e14fc1a]",
                                    "weight": 0.95,
                                    "image": ref_image,
                                    "pixel_perfect": True
                                },
                                {
                                    "enabled": True,
                                    "module": "inpaint",
                                    "model": "control_v11p_sd15_inpaint [ebff9138]",
                                    "weight": 0.8,
                                    "image": current_b64,
                                    "mask": face_mask_b64,
                                    "pixel_perfect": True
                                }
                            ]
                        }
                    }
                }
                if not request.use_ip_adapter:
                    face_payload["alwayson_scripts"]["controlnet"]["args"] = [
                        arg for arg in face_payload["alwayson_scripts"]["controlnet"]["args"]
                        if arg.get("module") != "ip-adapter_face_id_plus"
                    ]
                logger.info("🧩 [Compose Dual] Refining %s face...", side)
                try:
                    r = await client.post(SD_IMG2IMG_URL, json=face_payload, timeout=120.0)
                    r.raise_for_status()
                    data = r.json()
                except httpx.HTTPStatusError as e:
                    err_text = e.response.text if e.response is not None else ""
                    if "Insightface: No face found" in err_text and request.use_ip_adapter:
                        if request.strict_identity:
                            raise HTTPException(
                                status_code=400,
                                detail="Reference image must contain a clear face for identity locking."
                            )
                        logger.warning("⚠️ No face found in reference image. Retrying face refine without IP-Adapter...")
                        face_payload["alwayson_scripts"]["controlnet"]["args"] = [
                            arg for arg in face_payload["alwayson_scripts"]["controlnet"]["args"]
                            if arg.get("module") != "ip-adapter_face_id_plus"
                        ]
                        r = await client.post(SD_IMG2IMG_URL, json=face_payload, timeout=120.0)
                        r.raise_for_status()
                        data = r.json()
                    else:
                        raise
                current_b64 = data.get("images", [None])[0]
                if not current_b64:
                    raise HTTPException(status_code=500, detail=f"{side} face refine failed")

            info = json.loads(data.get("info", "{}"))
            return {"image": current_b64, "seed": info.get("seed", -1)}
        except Exception as e:
            logger.error(f"❌ Compose Dual Failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/debug/webui_compose_test")
async def webui_compose_test(request: WebUIComposeTestRequest):
    width, height = request.width, request.height
    base_img = Image.new("RGB", (width, height), (25, 25, 25))
    draw = ImageDraw.Draw(base_img)
    draw.rectangle([0, int(height * 0.6), width, height], fill=(40, 40, 40))
    draw.rectangle([0, 0, width, int(height * 0.2)], fill=(18, 18, 18))

    mask_img = Image.new("L", (width, height), 0)
    mask_draw = ImageDraw.Draw(mask_img)
    radius = int(min(width, height) * 0.25)
    cx, cy = width // 2, int(height * 0.55)
    mask_draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=255)

    base_b64 = image_to_base64(base_img)
    mask_b64 = image_to_base64(mask_img)

    payload = {
        "prompt": request.prompt,
        "negative_prompt": DEFAULT_NEGATIVE_PROMPT,
        "steps": request.steps,
        "width": width,
        "height": height,
        "sampler_name": "DPM++ 2M Karras",
        "cfg_scale": request.cfg_scale,
        "seed": -1,
        "init_images": [base_b64],
        "mask": mask_b64,
        "mask_blur": 8,
        "inpainting_fill": 1,
        "inpaint_full_res": True,
        "inpaint_full_res_padding": 32,
        "denoising_strength": request.denoising_strength,
        "alwayson_scripts": {
            "controlnet": {
                "args": [
                    {
                        "enabled": True,
                        "module": "segmentation",
                        "model": "control_v11p_sd15_seg [e1f51eb9]",
                        "weight": 0.6,
                        "image": base_b64,
                        "pixel_perfect": True
                    },
                    {
                        "enabled": True,
                        "module": "inpaint",
                        "model": "control_v11p_sd15_inpaint [ebff9138]",
                        "weight": 0.8,
                        "image": base_b64,
                        "mask": mask_b64,
                        "pixel_perfect": True
                    }
                ]
            }
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            logger.info("🧪 [WebUI Compose Test] Sending img2img request...")
            r = await client.post(SD_IMG2IMG_URL, json=payload, timeout=120.0)
            r.raise_for_status()
            data = r.json()
            info = json.loads(data.get("info", "{}"))
            return {
                "image": data.get("images", [None])[0],
                "seed": info.get("seed", -1),
                "used_models": ["control_v11p_sd15_seg [e1f51eb9]", "control_v11p_sd15_inpaint [ebff9138]"]
            }
        except Exception as e:
            logger.error(f"❌ WebUI Compose Test Failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/storyboard/create")
async def create_storyboard(request: StoryboardRequest):
    if not gemini_client: raise HTTPException(status_code=503, detail="Gemini key missing")
    try:
        template = template_env.get_template("create_storyboard.j2")
        system_instruction = f"SYSTEM: Professional storyboarder and scriptwriter. Write CONCISE, punchy scripts in {request.language} (max 40 chars). NO EMOJIS."
        res = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp", 
            contents=f"{system_instruction}\n\n{template.render(topic=request.topic, duration=request.duration, style=request.style, structure=request.structure, characters=request.characters)}"
        )
        return {"scenes": json.loads(res.text.strip().replace("```json", "").replace("```", ""))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/video/create")
async def create_video(request: VideoRequest):
    logger.info(f"🎬 [영상 제작 시작 - v2.0 Safe Mode] 프로젝트: {request.project_name}")
    logger.info(f"📏 요청 해상도: {request.width}x{request.height}")
    
    # Force override to Shorts (1080x1920) if Square (512x512) is requested, 
    # to fix the issue where users get square videos due to old settings.
    target_w, target_h = request.width, request.height
    if target_w == 512 and target_h == 512:
        logger.info("🔄 512x512 요청 감지 -> 1080x1920(Shorts)로 강제 변환합니다.")
        target_w, target_h = 1080, 1920

    project_id = f"build_{int(time.time())}"
    temp_dir = IMAGE_DIR / project_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    video_filename = f"{request.project_name}_{int(time.time())}.mp4"
    video_path = VIDEO_DIR / video_filename
    
    font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
    if not os.path.exists(font_path): font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"

    try:
        input_args = []
        num_scenes = len(request.scenes)
        TRANSITION_DUR = 0.5 # Faster transition for shorts

        for i, scene in enumerate(request.scenes):
            img_path = temp_dir / f"scene_{i}.png"
            tts_path = temp_dir / f"tts_{i}.mp3"
            txt_file = temp_dir / f"text_{i}.txt"
            img_path.write_bytes(base64.b64decode(scene["image_url"].split(",")[1]))
            
            # Script processing
            raw_script = scene.get('script', '')
            clean_script = re.sub(r'[^\w\s.,!?가-힣a-zA-Zぁ-ゔァ-ヴー々〆〤一-龥]', '', raw_script).replace("'", "").strip()
            # Split long lines for subtitles
            wrapped_script = wrap_text(clean_script, width=20) 
            txt_file.write_text(wrapped_script, encoding="utf-8")
            
            has_valid_tts = False
            if txt_for_tts := raw_script.replace("'", "").strip():
                try:
                    # Determine voice based on speaker
                    speaker = scene.get('speaker', 'Narrator')
                    voice = request.narrator_voice or "ko-KR-SunHiNeural" # Default to narrator voice
                    
                    if speaker == "A" and len(request.characters) > 0:
                        voice = request.characters[0].voice
                    elif speaker == "B" and len(request.characters) > 1:
                        voice = request.characters[1].voice
                        
                    communicate = edge_tts.Communicate(txt_for_tts, voice)
                    await communicate.save(str(tts_path))
                    if tts_path.exists() and tts_path.stat().st_size > 0: has_valid_tts = True
                except: pass

            input_args.extend(["-loop", "1", "-i", str(img_path)])
            if has_valid_tts: input_args.extend(["-i", str(tts_path)])
            else: input_args.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])

        filters = []
        # Use determined width/height (Force 1080x1920 if 512x512 was requested)
        out_w, out_h = (target_w, target_h)
        
        # Asset Paths for FFmpeg (Escaped for Filter Graph)
        # On macOS/Linux, colon escaping is usually not needed inside single quotes, but backslash is.
        # We replace backslash with forward slash for safety.
        abs_font_path = str(pathlib.Path(font_path).resolve()).replace("\\", "/")

        for i in range(num_scenes):
            v_idx, base_dur = i * 2, request.scenes[i].get('duration', 3)
            
            txt_file = temp_dir / f"text_{i}.txt"
            abs_txt_path = str(txt_file.resolve()).replace("\\", "/")
            
            if request.scenes[i].get('script'):
                tts_p = temp_dir / f"tts_{i}.mp3"
                if tts_p.exists(): base_dur = max(base_dur, get_audio_duration(tts_p) + 0.5)
            
            clip_dur = base_dur + (TRANSITION_DUR if i < num_scenes - 1 else 0)
            
            # Simplified Filter Chain (ZoomPan removed for stability)
            # 1. Scale & Crop to Square -> 2. Draw Text -> 3. Trim
            
            text_style = "fontcolor=white:fontsize=65:borderw=7:bordercolor=black:shadowx=3:shadowy=3"
            text_y_pos = "250"
            
            # Step 1: Blurred Background + Centered Image
            # [v_idx] -> Split -> [bg] (scale/crop/blur)
            #                  -> [fg] (scale fit)
            # [bg][fg]Overlay -> [v_base]
            
            # Note: We need to use split to use the input stream twice.
            # But since we use -loop 1, we can't easily split the infinite stream inside the filter without care.
            # Actually, simpler is to just scale/crop the input to BG, and use input AGAIN for FG? 
            # No, filter graph consumes the input pad. We must split.
            
            # Complex filter string construction:
            # [v_idx]split=2[v{i}_in_bg][v{i}_in_fg];
            # [v{i}_in_bg]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,crop={out_w}:{out_h},boxblur=40:20[v{i}_bg_blurred];
            # [v{i}_in_fg]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease[v{i}_fg_scaled];
            # [v{i}_bg_blurred][v{i}_fg_scaled]overlay=(W-w)/2:(H-h)/2:format=auto[v{i}_comp];
            # [v{i}_comp]drawtext...
            
            # To avoid variable collision in a loop, we name pads uniquely with {i}.
            
            filters.append(f"[{v_idx}:v]split=2[v{i}_in_1][v{i}_in_2]")
            
            # Background layer
            filters.append(f"[v{i}_in_1]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,crop={out_w}:{out_h},boxblur=40:20[v{i}_bg]")
            
            # Foreground layer (Fit)
            filters.append(f"[v{i}_in_2]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease[v{i}_fg]")
            
            # Composite
            filters.append(f"[v{i}_bg][v{i}_fg]overlay=(W-w)/2:(H-h)/2:format=auto[v{i}_base]")
            
            # Step 2: Draw Text (on composite)
            filters.append(f"[v{i}_base]drawtext=fontfile='{abs_font_path}':textfile='{abs_txt_path}':{text_style}:x=(w-text_w)/2:y={text_y_pos}[v{i}_text]")
            
            # Step 3: Trim & SetPTS
            filters.append(f"[v{i}_text]trim=duration={clip_dur},setpts=PTS-STARTPTS[v{i}_raw]")

        # Audio Chain
        for i in range(num_scenes):
            a_idx = i * 2 + 1
            clip_dur = request.scenes[i].get('duration', 3)
            if request.scenes[i].get('script'):
                tts_p = temp_dir / f"tts_{i}.mp3"
                if tts_p.exists(): clip_dur = max(clip_dur, get_audio_duration(tts_p) + 0.5)
            clip_dur += (TRANSITION_DUR if i < num_scenes - 1 else 0)
            filters.append(f"[{a_idx}:a]aresample=44100,aformat=channel_layouts=stereo,apad,atrim=duration={clip_dur},asetpts=PTS-STARTPTS[a{i}_raw]")

        # Concat with Crossfade
        if num_scenes > 1:
            curr_v, curr_a, acc_offset = "[v0_raw]", "[a0_raw]", 0
            for i in range(1, num_scenes):
                # Calculate offset based on previous clip's actual duration (minus transition overlap)
                prev_dur = request.scenes[i-1].get('duration', 3)
                if request.scenes[i-1].get('script'):
                    tts_p = temp_dir / f"tts_{i-1}.mp3"
                    if tts_p.exists(): prev_dur = max(prev_dur, get_audio_duration(tts_p) + 0.5)
                
                acc_offset += prev_dur
                
                filters.append(f"{curr_v}[v{i}_raw]xfade=transition=fade:duration={TRANSITION_DUR}:offset={acc_offset}[v{i}_m]")
                curr_v = f"[v{i}_m]"
                filters.append(f"{curr_a}[a{i}_raw]acrossfade=d={TRANSITION_DUR}:o=1:c1=tri:c2=tri[a{i}_m]")
                curr_a = f"[a{i}_m]"
            map_v, map_a = curr_v, curr_a
            
            # Calculate total duration for BGM fade out
            last_dur = request.scenes[-1].get('duration', 3)
            if request.scenes[-1].get('script'):
                tts_p = temp_dir / f"tts_{num_scenes-1}.mp3"
                if tts_p.exists(): last_dur = max(last_dur, get_audio_duration(tts_p) + 0.5)
            total_dur = acc_offset + last_dur
        else:
            map_v, map_a = "[v0_raw]", "[a0_raw]"
            total_dur = request.scenes[0].get('duration', 3)
            if request.scenes[0].get('script'):
                tts_p = temp_dir / f"tts_0.mp3"
                if tts_p.exists(): total_dur = max(total_dur, get_audio_duration(tts_p) + 0.5)

        bgm_path = AUDIO_DIR / request.bgm_file if request.bgm_file else None
        next_input_idx = num_scenes * 2
        
        # Watermark
        filters.append(f"{map_v}drawtext=text='Shorts Producer AI':fontcolor=white@0.5:fontsize=24:x=w-tw-40:y=40[v_w]")
        current_v = "[v_w]"

        # SNS Overlay (If enabled)
        if request.overlay_settings and request.overlay_settings.enabled:
            overlay_img_path = temp_dir / "custom_overlay.png"
            create_dynamic_overlay(request.overlay_settings, overlay_img_path, width=out_w, height=out_h)
            input_args.extend(["-i", str(overlay_img_path)])
            filters.append(f"{current_v}[{next_input_idx}:v]overlay=0:0[v_o]")
            current_v, next_input_idx = "[v_o]", next_input_idx + 1
            
        # BGM Mixing
        if bgm_path and bgm_path.exists():
            input_args.extend(["-i", str(bgm_path)])
            filters.append(f"[{next_input_idx}:a]volume=0.15,afade=t=out:st={max(0, total_dur-2)}:d=2[bgm_f]")
            filters.append(f"{map_a}[bgm_f]amix=inputs=2:duration=first:dropout_transition=2[a_f]")
            map_a = "[a_f]"
            
        filter_complex_str = ";".join(filters)
        cmd = ["ffmpeg", "-y"] + input_args + [
            "-filter_complex", filter_complex_str, 
            "-map", current_v, 
            "-map", map_a, 
            "-s", f"{out_w}x{out_h}", # Force exact output resolution
            "-c:v", "libx264", 
            "-pix_fmt", "yuv420p", 
            "-preset", "medium", 
            "-c:a", "aac", 
            "-b:a", "192k", 
            str(video_path)
        ]
        
        logger.info(f"Running FFmpeg: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg Stderr: {result.stderr}")
            raise Exception(f"FFmpeg failed: {result.stderr}")
            
        shutil.rmtree(temp_dir)
        return {"video_url": f"http://localhost:8000/outputs/videos/{video_filename}"}
    except Exception as e:
        import traceback
        logger.error(f"Video Create Error: {traceback.format_exc()}")
        if temp_dir.exists(): shutil.rmtree(temp_dir)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
