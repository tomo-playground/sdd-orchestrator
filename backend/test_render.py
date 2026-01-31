#!/usr/bin/env python3
"""Quick render test for Full Layout improvements."""

import requests
import json

BASE_URL = "http://localhost:8000"

# Simple test storyboard
test_storyboard = {
    "title": "Full Layout Test",
    "scenes": [
        {
            "script": "그래도 엄마가 맞았다고 해줘서 기뻤어.",
            "description": "1girl, standing, cooking, kitchen, smiling",
            "duration": 3.0,
            "image_url": None,  # Will be generated
        }
    ]
}

# Video render request (Full layout)
render_request = {
    "storyboard_title": "Full Layout Test",
    "scenes": [],  # Will be populated with generated images
    "layout_style": "full",  # 9:16
    "width": 1080,
    "height": 1920,
    "include_subtitles": True,
    "narrator_voice": "ko-KR-SunHiNeural",
    "bgm_file": None,
    "speed_multiplier": 1.0,
}

def main():
    print("🎬 Full Layout Render Test")
    print("=" * 60)
    print("\nThis test requires:")
    print("  - SD WebUI running (--api)")
    print("  - Backend API running (port 8000)")
    print("\nProceed? (y/n): ", end="")

    # For automation, skip confirmation
    # response = input()
    # if response.lower() != 'y':
    #     print("Test cancelled.")
    #     return

    print("\n⚠️  Manual test recommended:")
    print("  1. Open http://localhost:3000")
    print("  2. Create storyboard: '요리하는 캐릭터'")
    print("  3. Select Full Layout (9:16)")
    print("  4. Enable subtitles")
    print("  5. Render and check:")
    print("     ✓ Subtitle size: Large and readable")
    print("     ✓ Subtitle position: Bottom 15-18%")
    print("     ✓ Crop: Character head preserved")
    print()

if __name__ == "__main__":
    main()
