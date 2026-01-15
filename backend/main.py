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
SD_URL = "http://127.0.0.1:7860/sdapi/v1/txt2img"
SD_LORA_URL = "http://127.0.0.1:7860/sdapi/v1/loras"
SD_CONFIG_URL = "http://127.0.0.1:7860/sdapi/v1/options"
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
class GenerateRequest(BaseModel):
    prompt: str
    persona: str | None = None
    lora: str | None = None
    negative_prompt: str | None = None
    styles: list[str] = []
    width: int = 512
    height: int = 512
    seed: int = -1

class StoryboardRequest(BaseModel):
    topic: str
    duration: int = 30
    style: str = "Cinematic"
    language: str = "Korean"
    structure: str = "Free Flow" # Narrative Pattern

class VideoRequest(BaseModel):
    scenes: list[dict]
    project_name: str = "my_shorts"
    bgm_file: str | None = None
    voice: str = "ko-KR-SunHiNeural"
    width: int = 512
    height: int = 512

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

# --- FastAPI 앱 설정 ---
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
app.mount("/assets", StaticFiles(directory="assets"), name="assets") # 추가: BGM 접근용

@app.get("/loras")
async def get_loras():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(SD_LORA_URL, timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                # Ensure data is a list (Standard A1111 API)
                if isinstance(data, dict):
                    data = data.get("loras", [])
                
                if isinstance(data, list):
                    loras = []
                    for item in data:
                        if isinstance(item, dict):
                            name = item.get("name") or item.get("alias")
                            if name: loras.append(name)
                        elif isinstance(item, str):
                            loras.append(item)
                    return {"loras": sorted(list(set(loras)))}
            return {"loras": []}
    except Exception as e:
        logger.error(f"Lora fetch error: {e}")
        return {"loras": []}

@app.get("/config")
async def get_config():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(SD_CONFIG_URL, timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict):
                    return {"model": data.get("sd_model_checkpoint", "Unknown")}
            return {"model": "Offline"}
    except Exception as e:
        logger.error(f"Config fetch error: {e}")
        return {"model": "Offline"}

@app.get("/audio/list")
async def get_audio_list():
    try:
        extensions = ["*.mp3", "*.MP3", "*.wav", "*.WAV", "*.m4a", "*.M4A"]
        files = []
        for ext in extensions:
            for f in AUDIO_DIR.glob(ext):
                files.append({
                    "name": f.name,
                    "url": f"http://localhost:8000/assets/audio/{f.name}"
                })
        return {"audios": sorted(files, key=lambda x: x["name"])}
    except Exception as e:
        return {"audios": []}

@app.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    file_path = PROJECTS_DIR / f"{project_id}.json"
    if file_path.exists():
        file_path.unlink()
        return {"status": "success"}
    raise HTTPException(status_code=404)

@app.post("/projects/save")
async def save_project(request: ProjectSaveRequest):
    project_id = request.id or f"proj_{int(time.time())}"
    file_path = PROJECTS_DIR / f"{project_id}.json"
    project_data = {
        "id": project_id,
        "title": request.title,
        "updated_at": time.time(),
        "content": request.data
    }
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

@app.post("/generate")
async def generate_image(request: GenerateRequest):
    final_pos, final_neg = request.prompt, request.negative_prompt or DEFAULT_NEGATIVE_PROMPT
    if gemini_client:
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
        except: pass
    
    payload = {"prompt": f"{final_pos}, <lora:{request.lora}:1>" if request.lora else final_pos, "negative_prompt": final_neg, "steps": 20, "width": request.width, "height": request.height, "sampler_name": "Euler a", "cfg_scale": 7, "seed": request.seed}
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(SD_URL, json=payload, timeout=60.0)
            data = r.json()
            info = json.loads(data.get("info", "{}"))
            return {"images": data.get("images", []), "seed": info.get("seed", request.seed), "translated_prompt": final_pos, "negative_prompt": final_neg}
        except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/storyboard/create")
async def create_storyboard(request: StoryboardRequest):
    if not gemini_client: raise HTTPException(status_code=503, detail="Gemini key missing")
    try:
        template = template_env.get_template("create_storyboard.j2")
        system_instruction = f"SYSTEM: Professional storyboarder and scriptwriter. Write CONCISE, punchy scripts in {request.language} (max 40 chars). NO EMOJIS."
        res = gemini_client.models.generate_content(model="gemini-2.0-flash-exp", contents=f"{system_instruction}\n\n{template.render(topic=request.topic, duration=request.duration, style=request.style, structure=request.structure)}")
        return {"scenes": json.loads(res.text.strip().replace("```json", "").replace("```", ""))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/video/create")
async def create_video(request: VideoRequest):
    logger.info(f"🎬 [영상 제작 시작] 프로젝트: {request.project_name}")
    project_id = f"build_{int(time.time())}"
    temp_dir = IMAGE_DIR / project_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    video_filename = f"{request.project_name}_{int(time.time())}.mp4"
    video_path = VIDEO_DIR / video_filename
    
    font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
    if not os.path.exists(font_path): font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"

    try:
        # Step 1: Assets Preparation (Image, TTS, Text File)
        input_args = []
        num_scenes = len(request.scenes)
        TRANSITION_DUR = 0.7  # Crossfade duration (seconds)

        for i, scene in enumerate(request.scenes):
            img_path = temp_dir / f"scene_{i}.png"
            tts_path = temp_dir / f"tts_{i}.mp3"
            txt_file = temp_dir / f"text_{i}.txt"
            
            # Save Image
            img_path.write_bytes(base64.b64decode(scene["image_url"].split(",")[1]))
            
            # Save Text (Cleaned)
            raw_script = scene.get('script', '')
            txt_for_drawtext = re.sub(r'[^\w\s.,!?가-힣a-zA-Zぁ-ゔァ-ヴー々〆〤一-龥]', '', raw_script).replace("'", "").strip()
            txt_for_tts = raw_script.replace("'", "").strip()
            wrapped_txt = wrap_text(txt_for_drawtext, width=25)
            txt_file.write_text(wrapped_txt, encoding="utf-8")
            
            # Generate TTS
            has_valid_tts = False
            if txt_for_tts:
                try:
                    communicate = edge_tts.Communicate(txt_for_tts, request.voice)
                    await communicate.save(str(tts_path))
                    if tts_path.exists() and tts_path.stat().st_size > 0:
                        has_valid_tts = True
                except Exception as e:
                    logger.error(f"❌ TTS Error for scene {i}: {e}")

            # Inputs for FFmpeg: [Image, TTS(or silence)]
            input_args.extend(["-loop", "1", "-i", str(img_path)])
            if has_valid_tts:
                input_args.extend(["-i", str(tts_path)])
            else:
                input_args.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])

        # Step 2: Build Filter Complex for Crossfade
        filter_complex = ""
        
        # 2.1 Video Processing (ZoomPan + Subtitles)
        w, h = request.width, request.height
        for i in range(num_scenes):
            v_idx = i * 2
            
            # Calculate Duration
            # Base duration from TTS or user setting
            base_dur = request.scenes[i].get('duration', 3)
            if request.scenes[i].get('script'): # If there's script, ensure min duration covers it
                tts_p = temp_dir / f"tts_{i}.mp3"
                if tts_p.exists(): base_dur = max(base_dur, get_audio_duration(tts_p) + 0.5)
            
            # Actual duration needed for clip = Base + Transition Overlap (if not last)
            clip_dur = base_dur + (TRANSITION_DUR if i < num_scenes - 1 else 0)
            total_frames = int(clip_dur * 25)
            
            # Zigzag Text Position
            text_y_pos = "h-th-100" if i % 2 == 0 else "100"

            filter_complex += (
                f"[{v_idx}:v]scale={w*2}:{h*2},zoompan=z='min(zoom+0.0015,1.5)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h},"
                f"fps=25,format=yuv420p,settb=AVTB,setpts=PTS-STARTPTS,"
                f"drawtext=fontfile='{font_path}':textfile='{txt_file}':fontcolor=white:fontsize=32:line_spacing=12:borderw=2:bordercolor=black:box=1:boxcolor=black@0.6:boxborderw=20:x=(w-text_w)/2:y={text_y_pos}[v{i}_raw];"
            )

        # 2.2 Audio Processing (Pad to match video length)
        for i in range(num_scenes):
            a_idx = i * 2 + 1
            # Recalculate same duration logic
            base_dur = request.scenes[i].get('duration', 3)
            if request.scenes[i].get('script'):
                tts_p = temp_dir / f"tts_{i}.mp3"
                if tts_p.exists(): base_dur = max(base_dur, get_audio_duration(tts_p) + 0.5)
            
            clip_dur = base_dur + (TRANSITION_DUR if i < num_scenes - 1 else 0)
            
            # Process Audio
            filter_complex += f"[{a_idx}:a]aresample=44100,aformat=channel_layouts=stereo,apad=whole_dur={clip_dur},atrim=duration={clip_dur},asetpts=PTS-STARTPTS[a{i}_raw];"

        # 2.3 Crossfade Logic (Iterative)
        if num_scenes > 1:
            # Initialize with first scene
            curr_v = "[v0_raw]"
            curr_a = "[a0_raw]"
            
            # Start offset calculation
            # First scene ends at its base_dur (without transition overlap for next)
            # Actually, xfade offset is relative to START of the stream.
            # Scene 0 plays for base_dur. Scene 1 starts fading in at base_dur.
            
            accumulated_offset = 0
            
            for i in range(1, num_scenes):
                # Calculate offset for THIS transition
                # Previous scene's functional duration (before fade out starts)
                prev_base_dur = request.scenes[i-1].get('duration', 3)
                if request.scenes[i-1].get('script'):
                    tts_p = temp_dir / f"tts_{i-1}.mp3"
                    if tts_p.exists(): prev_base_dur = max(prev_base_dur, get_audio_duration(tts_p) + 0.5)
                
                accumulated_offset += prev_base_dur
                
                # Apply Xfade
                next_v = f"[v{i}_raw]"
                filter_complex += f"{curr_v}{next_v}xfade=transition=fade:duration={TRANSITION_DUR}:offset={accumulated_offset}[v{i}_merged];"
                curr_v = f"[v{i}_merged]"
                
                # Apply Acrossfade (Audio)
                next_a = f"[a{i}_raw]"
                # Acrossfade does not use offset time, it overlaps streams directly. 
                # Since we padded streams, we just need to tell it how much to overlap.
                # BUT wait, acrossfade consumes inputs. So a chain works: A+B -> AB, AB+C -> ABC
                filter_complex += f"{curr_a}{next_a}acrossfade=d={TRANSITION_DUR}:o=1:c1=tri:c2=tri[a{i}_merged];"
                curr_a = f"[a{i}_merged]"
            
            map_v = curr_v
            map_a = curr_a
            # Update accumulated offset to final duration for BGM fadeout
            last_dur = request.scenes[-1].get('duration', 3)
            if request.scenes[-1].get('script'):
                tts_p = temp_dir / f"tts_{num_scenes-1}.mp3"
                if tts_p.exists(): last_dur = max(last_dur, get_audio_duration(tts_p) + 0.5)
            accumulated_offset += last_dur

        else:
            # Single scene case
            map_v = "[v0_raw]"
            map_a = "[a0_raw]"
            accumulated_offset = request.scenes[0].get('duration', 3)

        # Step 4: Add BGM & Watermark
        bgm_path = AUDIO_DIR / request.bgm_file if request.bgm_file else None
        watermark_vf = "drawtext=text='Shorts Producer AI':fontcolor=white@0.3:fontsize=18:x=w-tw-30:y=h-th-30"
        
        final_input_idx = num_scenes * 2
        if bgm_path and bgm_path.exists():
            input_args.extend(["-i", str(bgm_path)])
            filter_complex += f"{map_v}{watermark_vf}[v_final];"
            # Fade out BGM at end
            filter_complex += f"[{final_input_idx}:a]volume=0.15,afade=t=out:st={max(0, accumulated_offset-2)}:d=2[bgm_faded];"
            # Mix
            filter_complex += f"{map_a}[bgm_faded]amix=inputs=2:duration=first:dropout_transition=2[a_final]"
            map_v, map_a = "[v_final]", "[a_final]"
        else:
            filter_complex += f"{map_v}{watermark_vf}[v_final]"
            map_v, map_a = "[v_final]", map_a

        # Execute FFmpeg
        cmd = ["ffmpeg", "-y"] + input_args + ["-filter_complex", filter_complex, "-map", map_v, "-map", map_a, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-c:a", "aac", "-b:a", "192k", str(video_path)]
        
        # Debug: Log command for troubleshooting
        # logger.info(f"FFmpeg Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg Error: {result.stderr}")
            raise Exception(f"FFmpeg rendering failed: {result.stderr}")

        shutil.rmtree(temp_dir)
        return {"video_url": f"http://localhost:8000/outputs/videos/{video_filename}"}
    except Exception as e: 
        logger.error(f"Video Creation Exception: {str(e)}")
        if temp_dir.exists(): shutil.rmtree(temp_dir)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)