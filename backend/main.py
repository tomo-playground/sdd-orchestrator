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

# 디렉토리 설정
CACHE_DIR = pathlib.Path(".cache")
OUTPUT_DIR = pathlib.Path("outputs")
IMAGE_DIR = OUTPUT_DIR / "images"
VIDEO_DIR = OUTPUT_DIR / "videos"
AUDIO_DIR = pathlib.Path("assets/audio")

for d in [CACHE_DIR, IMAGE_DIR, VIDEO_DIR, AUDIO_DIR]:
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

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# 데이터 모델
class GenerateRequest(BaseModel):
    prompt: str
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
    language: str = "Korean" # 추가: 언어 설정

class VideoRequest(BaseModel):
    scenes: list[dict]
    project_name: str = "my_shorts"
    bgm_file: str | None = None
    voice: str = "ko-KR-SunHiNeural"
    width: int = 512
    height: int = 512

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

# API 엔드포인트
SD_URL = "http://127.0.0.1:7860/sdapi/v1/txt2img"
SD_LORA_URL = "http://127.0.0.1:7860/sdapi/v1/loras"
SD_CONFIG_URL = "http://127.0.0.1:7860/sdapi/v1/options"
DEFAULT_NEGATIVE_PROMPT = "low quality, worst quality, bad anatomy, deformed, text, watermark, signature, ugly"

@app.get("/config")
async def get_config():
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(SD_CONFIG_URL, timeout=5.0)
            data = r.json()
            return {"model": data.get("sd_model_checkpoint", "Unknown")}
        except: return {"model": "Disconnected"}

@app.get("/loras")
async def get_loras():
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(SD_LORA_URL, timeout=5.0)
            return {"loras": [l["name"] for l in r.json()]}
        except: return {"loras": []}

@app.get("/audio/list")
async def get_audio_list():
    extensions = ["*.mp3", "*.MP3", "*.wav", "*.WAV", "*.m4a", "*.M4A"]
    files = []
    for ext in extensions: files.extend([f.name for f in AUDIO_DIR.glob(ext)])
    return {"audios": sorted(list(set(files)))}

@app.get("/video/list")
async def get_video_list():
    """제작된 영상 목록 반환"""
    videos = []
    for f in VIDEO_DIR.glob("*.mp4"):
        videos.append({
            "name": f.name,
            "url": f"http://localhost:8000/outputs/videos/{f.name}",
            "created_at": f.stat().st_mtime
        })
    # 최신순 정렬
    videos.sort(key=lambda x: x["created_at"], reverse=True)
    return {"videos": videos}

@app.delete("/video/{filename}")
async def delete_video(filename: str):
    file_path = VIDEO_DIR / filename
    if file_path.exists():
        file_path.unlink()
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="File not found")

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
        if not preview_path.exists():
            communicate = edge_tts.Communicate(request.text, request.voice)
            await communicate.save(str(preview_path))
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
            rendered = template.render(user_input=request.prompt, target_styles=", ".join(request.styles))
            h = hashlib.sha256(rendered.encode()).hexdigest()
            cache_file = CACHE_DIR / f"{h}.json"
            if cache_file.exists(): res_json = json.loads(cache_file.read_text(encoding="utf-8"))
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
            return {"images": data.get("images", []), "seed": info.get("seed", request.seed), "translated_prompt": final_pos}
        except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/storyboard/create")
async def create_storyboard(request: StoryboardRequest):
    if not gemini_client: raise HTTPException(status_code=503, detail="Gemini key missing")
    try:
        template = template_env.get_template("create_storyboard.j2")
        system_instruction = f"SYSTEM: Professional storyboarder. Write the 'script' field in {request.language}. NO EMOJIS. Plain text only."
        res = gemini_client.models.generate_content(model="gemini-2.0-flash-exp", contents=f"{system_instruction}\n\n{template.render(topic=request.topic, duration=request.duration, style=request.style)}")
        return {"scenes": json.loads(res.text.strip().replace("```json", "").replace("```", ""))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/video/create")
async def create_video(request: VideoRequest):
    project_id = f"{request.project_name}_{int(time.time())}"
    temp_dir = IMAGE_DIR / project_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    video_filename = f"{project_id}.mp4"
    video_path = VIDEO_DIR / video_filename
    font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
    if not os.path.exists(font_path): font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
    
    try:
        scene_clips, durations = [], []
        for i, scene in enumerate(request.scenes):
            img_path, clip_path, tts_path = temp_dir / f"scene_{i}.png", temp_dir / f"clip_{i}.mp4", temp_dir / f"tts_{i}.mp3"
            img_path.write_bytes(base64.b64decode(scene["image_url"].split(",")[1]))
            # 정규식에서 영어와 일본어도 허용하도록 수정
            txt = re.sub(r'[^\w\s.,!?가-힣a-zA-Zぁ-ゔァ-ヴー々〆〤一-龥]', '', scene['script']).replace("'", "").strip()
            wrapped_txt = wrap_text(txt)
            
            has_tts, audio_dur = False, 0
            if txt:
                try:
                    await edge_tts.Communicate(txt, request.voice).save(str(tts_path))
                    audio_dur = get_audio_duration(tts_path)
                    has_tts = True
                except: pass

            scene_dur = max(scene.get('duration', 3), audio_dur + 1.5)
            durations.append(scene_dur)
            total_frames = int(scene_dur * 25)
            w, h = request.width, request.height
            filter_complex = (
                f"[0:v]scale={w*2}:{h*2},zoompan=z='min(zoom+0.0015,1.5)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h},"
                f"fps=25,drawtext=fontfile='{font_path}':text='{wrapped_txt}':fontcolor=yellow:fontsize=36:line_spacing=12:borderw=4:bordercolor=black:x=(w-text_w)/2:y=h-th-100[v]"
            )
            cmd = ["ffmpeg", "-y", "-loop", "1", "-r", "25", "-i", str(img_path)]
            if has_tts: cmd.extend(["-i", str(tts_path), "-filter_complex", filter_complex, "-af", f"apad=pad_dur={scene_dur}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-map", "[v]", "-map", "1:a"])
            else: cmd.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100", "-filter_complex", filter_complex, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-map", "[v]", "-map", "1:a"])
            cmd.extend(["-frames:v", str(total_frames), str(clip_path)])
            subprocess.run(cmd, check=True, capture_output=True)
            scene_clips.append(f"clip_{i}.mp4")

        final_cmd = ["ffmpeg", "-y"]
        for i in range(len(scene_clips)): final_cmd.extend(["-i", str(temp_dir / f"clip_{i}.mp4")])
        v_filter = "[0:v][1:v]xfade=transition=fade:duration=1:offset=" + str(durations[0]-1) + "[v1]";
        current_offset = durations[0] + durations[1] - 2
        for i in range(2, len(scene_clips)):
            v_filter += f"[v{i-1}][{i}:v]xfade=transition=fade:duration=1:offset={current_offset}[v{i}];"
            current_offset += durations[i] - 1
        a_filter = "".join([f"[{i}:a]" for i in range(len(scene_clips))]) + f"concat=n={len(scene_clips)}:v=0:a=1[aout]";
        watermark_vf = "drawtext=text='Shorts Producer AI':fontcolor=white@0.3:fontsize=18:x=w-tw-30:y=h-th-30"
        bgm_path = AUDIO_DIR / request.bgm_file if request.bgm_file else None
        if bgm_path and bgm_path.exists():
            final_cmd.extend(["-i", str(bgm_path)])
            bgm_idx = len(scene_clips)
            bgm_fade = f"afade=t=out:st={current_offset+1-2}:d=2"
            filter_complex = v_filter + a_filter + f"[v{len(scene_clips)-1}]{watermark_vf}[vfinal];[{bgm_idx}:a]volume=0.15,{bgm_fade}[bgm];[aout][bgm]amix=inputs=2:duration=first[afinal]"
            final_cmd.extend(["-filter_complex", filter_complex, "-map", "[vfinal]", "-map", "[afinal]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest"])
        else:
            filter_complex = v_filter + a_filter + f"[v{len(scene_clips)-1}]{watermark_vf}[vfinal]"
            final_cmd.extend(["-filter_complex", filter_complex, "-map", "[vfinal]", "-map", "[aout]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac"])
        final_cmd.append(str(video_path))
        subprocess.run(final_cmd, check=True, capture_output=True)
        return {"video_url": f"http://localhost:8000/outputs/videos/{video_filename}"}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)