from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
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
SD_LORA_URL = f"{SD_BASE_URL}/sdapi/v1/loras"
SD_CONFIG_URL = f"{SD_BASE_URL}/sdapi/v1/options"
DEFAULT_NEGATIVE_PROMPT = "low quality, worst quality, bad anatomy, deformed, text, watermark, signature, ugly"

# 디렉토리 설정
CACHE_DIR = pathlib.Path(".cache")
OUTPUT_DIR = pathlib.Path("outputs")
IMAGE_DIR = OUTPUT_DIR / "images"
VIDEO_DIR = OUTPUT_DIR / "videos"
AUDIO_DIR = pathlib.Path("assets/audio")
PROJECTS_DIR = pathlib.Path("projects")

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
    lora: str | None = None
    negative_prompt: str | None = None
    styles: list[str] = []
    width: int = 512
    height: int = 512
    seed: int = -1
    skip_optimization: bool = False

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

class AudioGenerateRequest(BaseModel):
    prompt: str

class AudioPreviewRequest(BaseModel):
    text: str
    voice: str

# 유틸리티 함수
def get_audio_duration(path):
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return float(res.stdout.strip())
    except: return 0

def wrap_text(text, width=20):
    return "\n".join(textwrap.wrap(text, width=width))

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
        "prompt": f"{final_pos}, <lora:{request.lora}:1>" if request.lora else final_pos,
        "negative_prompt": final_neg,
        "steps": 20,
        "width": request.width,
        "height": request.height,
        "sampler_name": "Euler a",
        "cfg_scale": 7,
        "seed": request.seed
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
        except Exception as e:
            logger.error(f"❌ Image Generation Failed: {e}")
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
    
    font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
    if not os.path.exists(font_path): font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"

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
            txt_file.write_text(wrapped_script, encoding="utf-8-sig")
            
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
            
            text_style = "fontcolor=white:fontsize=65:borderw=5:bordercolor=black:shadowx=3:shadowy=3"
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
