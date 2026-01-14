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
from dotenv import load_dotenv
from google import genai
from jinja2 import Environment, FileSystemLoader

# 환경 변수 로드 (.env)
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("backend")

# 캐시 디렉토리 설정
CACHE_DIR = pathlib.Path(".cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Jinja2 템플릿 환경 설정
template_env = Environment(loader=FileSystemLoader("templates"))

# Gemini 클라이언트 초기화
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = None
if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("✨ [Gemini] 클라이언트 초기화 성공")
    except Exception as e:
        logger.error(f"❌ [Gemini] 초기화 실패: {e}")
else:
    logger.warning("⚠️ [Gemini] API 키가 없습니다. .env 파일을 확인해주세요.")

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    prompt: str
    lora: str | None = None
    negative_prompt: str | None = None
    styles: list[str] = []
    width: int = 512
    height: int = 512

# 로컬 Stable Diffusion API 주소
SD_URL = "http://127.0.0.1:7860/sdapi/v1/txt2img"
SD_LORA_URL = "http://127.0.0.1:7860/sdapi/v1/loras"
SD_CONFIG_URL = "http://127.0.0.1:7860/sdapi/v1/options"

# 기본 네거티브 프롬프트
DEFAULT_NEGATIVE_PROMPT = "low quality, worst quality, bad anatomy, deformed, text, watermark, signature, ugly"

@app.get("/config")
async def get_config():
    logger.info("⚙️ [설정 조회 요청] SD WebUI의 현재 설정을 가져옵니다.")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(SD_CONFIG_URL, timeout=10.0)
            response.raise_for_status()
            config = response.json()
            # 현재 모델명(체크포인트) 추출
            current_model = config.get("sd_model_checkpoint", "Unknown")
            return {
                "model": current_model,
                "all_options": config
            }
        except Exception as e:
            logger.error(f"❌ [오류] 설정 조회 실패: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/loras")
async def get_loras():
    # ... (기존 코드 유지)

@app.get("/random-prompt")
async def get_random_prompt():
    logger.info("🎲 [랜덤 프롬프트 생성 요청] Gemini에게 아이디어를 요청합니다.")
    if not gemini_client:
        return {"prompt": "눈 내리는 밤의 작은 카페"}
    
    try:
        instruction = (
            "Generate a creative and highly visual image description in Korean (one sentence). "
            "It should be something interesting to draw, like a fantasy scene, a futuristic city, or a cute character situation. "
            "Return ONLY the Korean text, no explanations or quotes."
        )
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=instruction
        )
        random_prompt = response.text.strip()
        logger.info(f"✨ [Gemini 아이디어] {random_prompt}")
        return {"prompt": random_prompt}
    except Exception as e:
        logger.error(f"❌ [오류] 랜덤 프롬프트 생성 실패: {e}")
        return {"prompt": "숲속의 신비로운 요정 마을"}

@app.post("/generate")
async def generate_image(request: GenerateRequest):
    start_time = time.time()
    original_prompt = request.prompt
    selected_lora = request.lora
    selected_styles = request.styles
    width = request.width
    height = request.height
    
    # 사용자 입력 네거티브 프롬프트 (없으면 None)
    user_negative = request.negative_prompt
    
    logger.info(f"📥 [요청 수신] 프롬프트: '{original_prompt}' | Size: {width}x{height} | Styles: {selected_styles} | LoRA: {selected_lora}")

    # 1. Gemini + Jinja2를 이용한 프롬프트 번역 및 최적화 (캐싱 적용)
    final_positive_prompt = original_prompt
    final_negative_prompt = DEFAULT_NEGATIVE_PROMPT
    
    # 사용자가 네거티브 프롬프트를 수정했는지 확인 (수정했으면 Gemini 제안보다 우선)
    is_negative_customized = user_negative is not None and user_negative != DEFAULT_NEGATIVE_PROMPT

    if gemini_client:
        try:
            # 스타일 리스트를 문자열로 변환
            style_str = ", ".join(selected_styles) if selected_styles else "None"

            # Jinja2 템플릿 로드 및 렌더링
            template = template_env.get_template("optimize_prompt.j2")
            rendered_prompt = template.render(
                user_input=original_prompt,
                target_styles=style_str
            )
            
            # 캐시 키 생성 (SHA256 해시) - 스타일이 바뀌면 해시도 바뀜
            prompt_hash = hashlib.sha256(rendered_prompt.encode("utf-8")).hexdigest()
            cache_file = CACHE_DIR / f"{prompt_hash}.json"

            gemini_result = {}

            if cache_file.exists():
                # 캐시 히트: 파일에서 읽기
                logger.info(f"💾 [캐시 히트] 저장된 프롬프트를 사용합니다. (Hash: {prompt_hash[:8]})")
                try:
                    gemini_result = json.loads(cache_file.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    logger.warning("⚠️ 캐시 파일 파손됨. 다시 생성합니다.")
            
            if not gemini_result:
                # 캐시 미스 또는 파손: Gemini 호출
                logger.info(f"☁️ [캐시 미스] Gemini API를 호출합니다...")
                response = gemini_client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=rendered_prompt
                )
                if response.text:
                    # JSON 파싱 시도 (마크다운 코드블록 제거 처리)
                    raw_text = response.text.strip().replace("```json", "").replace("```", "")
                    gemini_result = json.loads(raw_text)
                    # 결과 캐싱
                    cache_file.write_text(json.dumps(gemini_result, ensure_ascii=False, indent=2), encoding="utf-8")
                    logger.info("✨ [Gemini 최적화 & 저장 완료]")
            
            # 결과 적용
            if "positive_prompt" in gemini_result:
                final_positive_prompt = gemini_result["positive_prompt"]
                logger.info(f"➕ [Positive] {final_positive_prompt}")
            
            if "negative_prompt" in gemini_result:
                gemini_negative = gemini_result["negative_prompt"]
                logger.info(f"➖ [Negative(Gemini)] {gemini_negative}")
                
                # 사용자가 굳이 기본값을 건드리지 않았다면, Gemini가 추천한 것을 사용
                if not is_negative_customized:
                    final_negative_prompt = gemini_negative
                    logger.info("✅ Gemini가 제안한 네거티브 프롬프트를 적용합니다.")
                else:
                    final_negative_prompt = user_negative
                    logger.info(f"🔒 사용자가 지정한 네거티브 프롬프트를 유지합니다: {user_negative}")

        except Exception as e:
            logger.warning(f"⚠️ [Gemini 실패] 원본 프롬프트 사용. 오류: {e}")
            if is_negative_customized:
                final_negative_prompt = user_negative
    else:
        logger.info("ℹ️ [Gemini 미사용] 원본 프롬프트를 그대로 사용합니다.")
        if is_negative_customized:
            final_negative_prompt = user_negative

    # 2. LoRA 적용 (번역 후 추가)
    final_prompt_str = final_positive_prompt
    if selected_lora:
        final_prompt_str = f"{final_positive_prompt}, <lora:{selected_lora}:1>"
        logger.info(f"🎨 [LoRA 적용] 최종 프롬프트: {final_prompt_str}")

    # 3. Stable Diffusion API 호출
    payload = {
        "prompt": final_prompt_str,
        "negative_prompt": final_negative_prompt,
        "steps": 20,           # 샘플링 스텝 수
        "width": width,
        "height": height,
        "sampler_name": "Euler a", # 샘플러 (필요 시 변경)
        "cfg_scale": 7
    }

    logger.info(f"🚀 [SD API 요청] URL: {SD_URL}")
    logger.info(f"📦 [SD API 파라미터] {payload}")

    async with httpx.AsyncClient() as client:
        try:
            sd_start = time.time()
            # 타임아웃을 넉넉하게 설정 (이미지 생성 시간 고려)
            response = await client.post(SD_URL, json=payload, timeout=60.0)
            sd_duration = time.time() - sd_start
            
            logger.info(f"⏱️ [SD API 응답] 상태 코드: {response.status_code} | 소요 시간: {sd_duration:.2f}초")
            
            response.raise_for_status()
            
            result = response.json()
            images = result.get("images", [])
            
            logger.info(f"✅ [생성 완료] 이미지 {len(images)}장 생성됨. 총 처리 시간: {time.time() - start_time:.2f}초")
            
            # 결과 반환 (Base64 이미지 문자열 포함)
            return {
                "images": images,
                "translated_prompt": final_positive_prompt,
                "negative_prompt": final_negative_prompt
            }
        except httpx.ConnectError:
             logger.error("❌ [연결 오류] Stable Diffusion WebUI에 연결할 수 없습니다. (Connection Refused)")
             raise HTTPException(status_code=503, detail="Stable Diffusion WebUI에 연결할 수 없습니다. 실행 중인지 확인해주세요 (--api 옵션 필요).")
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ [HTTP 오류] SD API 응답 오류: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"SD API 오류: {e.response.text}")
        except Exception as e:
            logger.error(f"❌ [시스템 오류] 예상치 못한 오류 발생: {e}")
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
