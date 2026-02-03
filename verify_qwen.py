import asyncio
from pathlib import Path
import sys
import os

# 백엔드 경로 추가
sys.path.append(os.path.abspath("backend"))

from services.video.scene_processing import generate_tts
from unittest.mock import MagicMock

async def verify_qwen_tts():
    print("Testing Qwen3-TTS Local Integration...")
    
    # Mock 빌더 설정
    builder = MagicMock()
    builder.tts_rate = "+0%"
    builder.request.narrator_voice = "ko-KR-SunHiNeural"
    builder._get_audio_duration = lambda p: 2.0 # 더미 duration
    
    test_script = "안녕하세요, 큐wen3 TTS 로컬 설치 테스트입니다. 목소리가 잘 나오나요?"
    output_path = Path("test_qwen_out.mp3")
    
    if output_path.exists():
        output_path.unlink()

    print(f"Generating voice for: '{test_script}'")
    success, duration = await generate_tts(builder, 0, test_script, output_path)
    
    if success and output_path.exists():
        print(f"✅ Success! File saved to {output_path}")
        print(f"Generated duration: {duration}s")
    else:
        print("❌ Failed to generate voice.")

if __name__ == "__main__":
    asyncio.run(verify_qwen_tts())
