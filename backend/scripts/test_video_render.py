#!/usr/bin/env python3
"""Test video rendering with existing images."""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import json  # noqa: E402

import httpx  # noqa: E402

API_BASE = "http://localhost:8000"

def test_video_render():
    """Test video rendering with minimal scene data."""

    # Use existing images
    images = [
        "scene_000793d9c903170b.png",
        "scene_0021ec9b907c5ccd.png",
        "scene_0076b49895eec4cd.png",
    ]

    # Create test request (matching VideoRequest schema)
    # Use /outputs/ prefix for backend image loading
    request_data = {
        "scenes": [
            {
                "image_url": f"/outputs/images/stored/{img}",
                "script": f"테스트 씬 {i+1}입니다.",
                "speaker": "Narrator",
                "duration": 3.0,
            }
            for i, img in enumerate(images)
        ],
        "narrator_voice": "ko-KR-SunHiNeural",
        "bgm_file": None,
        "bgm_volume": 0.25,
        "audio_ducking": True,
        "overlay_settings": {
            "channel_name": "테스트 채널",
            "avatar_key": "test_channel",
            "caption": "테스트 영상 #shorts",
            "frame_style": "overlay_minimal.png",
        },
        "layout_style": "full",
        "width": 1080,
        "height": 1920,
        "transition_type": "fade",
        "ken_burns_preset": "none",
        "ken_burns_intensity": 1.0,
        "include_scene_text": True,
        "speed_multiplier": 1.0,
    }

    print("📤 Sending video render request...")
    print(f"   Scenes: {len(request_data['scenes'])}")
    print(f"   Layout: {request_data['layout_style']}")
    print(f"   Resolution: {request_data['width']}x{request_data['height']}")

    try:
        with httpx.Client(timeout=300.0) as client:
            response = client.post(
                f"{API_BASE}/video/create",
                json=request_data,
            )

            if response.status_code == 200:
                result = response.json()
                print("\n✅ Video rendering successful!")
                print(f"   Full response: {json.dumps(result, indent=2, ensure_ascii=False)}")
                print(f"   Output: {result.get('output_path')}")
                print(f"   Duration: {result.get('duration')} seconds")
                print(f"   Resolution: {result.get('resolution')}")
                return True
            else:
                print("\n❌ Video rendering failed!")
                print(f"   Status: {response.status_code}")
                print(f"   Error: {response.text}")
                return False

    except Exception as e:
        print(f"\n❌ Request failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Video Rendering Test")
    print("=" * 50)
    print()

    success = test_video_render()

    print()
    print("=" * 50)
    if success:
        print("✅ TEST PASSED")
    else:
        print("❌ TEST FAILED")
    print("=" * 50)

    sys.exit(0 if success else 1)
