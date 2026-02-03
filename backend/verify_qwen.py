import logging
import os
import time

import torch
from qwen_tts import Qwen3TTSModel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_qwen():
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    logger.info(f"Using device: {device}")

    model_id = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
    output_path = "test_qwen_out.mp3"

    try:
        logger.info(f"Loading model: {model_id}...")
        # 최적화 설정(M4 Pro): bfloat16 및 SDPA 적용
        # Wrapper 객체의 내부 모델을 이동시키고 device 속성도 명시적으로 업데이트
        model = Qwen3TTSModel.from_pretrained(
            model_id,
            dtype=torch.bfloat16 if device == "mps" else torch.float32,
            attn_implementation="sdpa"
        )
        model.model.to(device)
        model.device = torch.device(device)

        test_text = "안녕하세요. 로컬 Qwen3 TTS 엔진이 정상적으로 작동 중입니다. 만나서 반가워요!"

        logger.info(f"Generating audio for: '{test_text}'")
        start_time = time.time()

        # Voice Design 프롬프트 테스트
        voice_design = "밝고 활기찬 목소리"

        # generate_voice_design API 시용 (모델 타입에 맞춰야 함)
        wavs, sr = model.generate_voice_design(
            text=test_text,
            instruct=voice_design
        )

        import soundfile as sf
        sf.write(output_path, wavs[0], sr)

        end_time = time.time()

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"SUCCESS! Audio saved to {output_path}")
            logger.info(f"Generation time: {end_time - start_time:.2f} seconds")
        else:
            logger.error("FAILED! Output file is empty or does not exist.")

    except Exception as e:
        logger.error(f"Error during verification: {e}")

if __name__ == "__main__":
    verify_qwen()
