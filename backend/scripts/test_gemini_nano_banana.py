"""Gemini Nano Banana (2.5 Flash Image) 테스트 - 유레카 캐릭터

Gemini의 이미지 편집 기능을 사용하여 포즈/액션/표정 변경 효과를 검증합니다.

테스트 카테고리:
- Pose Editing: standing → sitting, jumping 등
- Action Editing: waving, pointing 등
- Expression Editing: smile → frown, neutral → surprised 등
- Gaze Editing: front → looking back 등
"""
import asyncio
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Backend 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# 유레카 캐릭터 베이스 프롬프트
EUREKA_BASE = "aqua_hair, short_hair, 1girl, chibi, purple_eyes, hairclip, t-shirt, <lora:eureka:1.0>, <lora:chibi:0.6>"

# 테스트 케이스 (유레카 특화)
TEST_CASES = [
    {
        "id": "eureka_standing_to_sitting",
        "name": "유레카: Standing → Sitting",
        "base_prompt": f"{EUREKA_BASE}, standing, arms_at_sides, indoors, classroom, cowboy_shot",
        "target_change": "sitting on chair with hands on lap",
        "expected_add": ["sitting", "chair"],
        "expected_remove": ["standing"],
        "difficulty": "easy",
    },
    {
        "id": "eureka_waving",
        "name": "유레카: Neutral → Waving",
        "base_prompt": f"{EUREKA_BASE}, standing, arms_at_sides, outdoors, cowboy_shot, smiling",
        "target_change": "waving with right hand raised",
        "expected_add": ["waving", "hand_up", "arm_up"],
        "expected_remove": ["arms_at_sides"],
        "difficulty": "easy",
    },
    {
        "id": "eureka_pointing",
        "name": "유레카: Neutral → Pointing",
        "base_prompt": f"{EUREKA_BASE}, standing, outdoors, cowboy_shot",
        "target_change": "pointing forward with right index finger",
        "expected_add": ["pointing", "arm_up"],
        "expected_remove": [],
        "difficulty": "easy",
    },
    {
        "id": "eureka_looking_back",
        "name": "유레카: Front → Looking Back",
        "base_prompt": f"{EUREKA_BASE}, standing, looking_at_viewer, cowboy_shot, outdoors",
        "target_change": "back view, looking back over shoulder at viewer",
        "expected_add": ["from_behind", "looking_back"],
        "expected_remove": [],
        "difficulty": "medium",
    },
    {
        "id": "eureka_jumping",
        "name": "유레카: Standing → Jumping",
        "base_prompt": f"{EUREKA_BASE}, standing, outdoors, full_body",
        "target_change": "jumping in the air with arms spread",
        "expected_add": ["jumping", "midair", "arms_up"],
        "expected_remove": ["standing"],
        "difficulty": "hard",
    },
    # Expression Editing Tests (Phase 1.5)
    {
        "id": "eureka_smile_to_frown",
        "name": "유레카: Smiling → Frowning",
        "base_prompt": f"{EUREKA_BASE}, standing, smile, looking_at_viewer, cowboy_shot, indoors",
        "target_change": "change expression to frowning with concerned look",
        "expected_add": ["frown", "worried"],
        "expected_remove": ["smile"],
        "difficulty": "easy",
    },
    {
        "id": "eureka_neutral_to_surprised",
        "name": "유레카: Neutral → Surprised",
        "base_prompt": f"{EUREKA_BASE}, standing, closed_mouth, looking_at_viewer, cowboy_shot, indoors",
        "target_change": "change expression to surprised with open mouth and wide eyes",
        "expected_add": ["surprised", "open_mouth", "wide-eyed"],
        "expected_remove": ["closed_mouth"],
        "difficulty": "easy",
    },
]


class ImagenTester:
    """Vertex AI Imagen 3 테스터"""

    def __init__(self, output_dir: str = "test_results/vertex_imagen"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.output_dir / self.session_id
        self.session_dir.mkdir(exist_ok=True)

        self.results = []

        # Gemini API 초기화
        self._init_gemini_api()

    def _init_gemini_api(self):
        """Gemini API 초기화 및 환경 체크"""
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            print("⚠️  GEMINI_API_KEY not set")
            print("   Get your API key from: https://aistudio.google.com/apikey")
            print("   Set it with: export GEMINI_API_KEY=your-api-key")
            self.gemini_available = False
            return

        try:
            from google import genai

            self.genai_client = genai.Client(api_key=api_key)
            self.gemini_available = True

            print(f"✅ Gemini API initialized")
            print(f"   Model: gemini-2.5-flash-image (Nano Banana)")

        except Exception as e:
            print(f"❌ Gemini API initialization failed: {e}")
            print(f"   Install: pip install google-genai")
            self.gemini_available = False

    async def run_all_tests(self, limit: int | None = None, use_mock: bool = False, test_ids: list[str] | None = None):
        """모든 테스트 실행"""
        if test_ids:
            test_cases = [tc for tc in TEST_CASES if tc["id"] in test_ids]
        elif limit:
            test_cases = TEST_CASES[:limit]
        else:
            test_cases = TEST_CASES

        if not self.gemini_available and not use_mock:
            print("\n❌ Gemini API not available. Use --mock flag to test pipeline only.")
            print("   Get your API key from: https://aistudio.google.com/apikey")
            return

        print(f"\n{'='*70}")
        print(f"🧪 Gemini Nano Banana Test Suite - Eureka Character")
        print(f"{'='*70}")
        print(f"📁 Output: {self.session_dir}")
        print(f"📊 Test cases: {len(test_cases)}")
        print(f"🎨 Mode: {'MOCK (no API calls)' if use_mock else 'REAL (API calls, costs apply)'}")
        print(f"{'='*70}\n")

        for i, test_case in enumerate(test_cases, 1):
            print(f"[{i}/{len(test_cases)}] {test_case['name']}")
            print(f"Difficulty: {test_case['difficulty']}")

            try:
                result = await self.run_single_test(test_case, use_mock=use_mock)
                self.results.append(result)
                self._print_result(result)

            except Exception as e:
                print(f"❌ Test failed: {str(e)}")
                import traceback
                traceback.print_exc()
                self.results.append({
                    "test_id": test_case["id"],
                    "status": "error",
                    "error": str(e),
                })

            print()

        # 최종 리포트
        self._generate_report()

    async def run_single_test(self, test_case: dict, use_mock: bool = False) -> dict:
        """단일 테스트 실행"""
        test_id = test_case["id"]

        # Step 1: SD로 베이스 이미지 생성
        print("  🎨 [1/5] Generating base image with SD...")
        base_image_b64 = await self._generate_with_sd(test_case["base_prompt"])
        base_path = self.session_dir / f"{test_id}_1_base.png"
        self._save_image(base_image_b64, base_path)
        print(f"      ✅ Saved: {base_path.name}")

        # Step 2: WD14로 베이스 분석
        print("  🔍 [2/5] Analyzing base with WD14...")
        base_tags = await self._analyze_with_wd14(base_image_b64)
        base_tag_names = [t["tag"] for t in base_tags[:30]]
        print(f"      📋 {len(base_tags)} tags detected")

        # Step 3: Gemini Vision 분석
        print("  👁️  [3/5] Analyzing with Gemini Vision...")
        vision_result = await self._analyze_with_gemini(
            base_image_b64,
            test_case["base_prompt"],
            test_case["target_change"],
        )
        print(f"      💬 Target: {vision_result['target_pose']}")

        # Step 4: Gemini Nano Banana로 편집
        print(f"  🎨 [4/5] {'Editing' if not use_mock else 'MOCK editing'} with Gemini Nano Banana...")
        if use_mock:
            edited_image_b64 = base_image_b64  # Mock: 원본 그대로
            edit_cost = 0.0
            print(f"      ⚠️  Mock mode: no actual editing")
        else:
            edit_result = await self._edit_with_gemini(
                base_image_b64,
                vision_result["target_pose"],
                vision_result.get("preserve_elements", []),
            )
            edited_image_b64 = edit_result["edited_image"]
            edit_cost = edit_result["cost"]

        edited_path = self.session_dir / f"{test_id}_2_edited.png"
        self._save_image(edited_image_b64, edited_path)
        print(f"      ✅ Saved: {edited_path.name}")

        # Step 5: WD14로 편집 후 분석
        print("  🔍 [5/5] Analyzing edited with WD14...")
        edited_tags = await self._analyze_with_wd14(edited_image_b64)
        edited_tag_names = [t["tag"] for t in edited_tags[:30]]
        print(f"      📋 {len(edited_tags)} tags detected")

        # 평가
        evaluation = self._evaluate(
            base_tag_names,
            edited_tag_names,
            test_case["expected_add"],
            test_case["expected_remove"],
        )

        total_cost = 0.0003 + edit_cost  # Gemini Vision + Imagen

        return {
            "test_id": test_id,
            "name": test_case["name"],
            "difficulty": test_case["difficulty"],
            "status": "completed",
            "base_prompt": test_case["base_prompt"],
            "target_change": test_case["target_change"],
            "expected_add": test_case["expected_add"],
            "expected_remove": test_case["expected_remove"],
            "base_tags": base_tag_names,
            "edited_tags": edited_tag_names,
            "vision_analysis": vision_result,
            "evaluation": evaluation,
            "cost_usd": total_cost,
            "files": {
                "base": str(base_path.relative_to(self.output_dir)),
                "edited": str(edited_path.relative_to(self.output_dir)),
            },
        }

    async def _generate_with_sd(self, prompt: str) -> str:
        """SD WebUI로 이미지 생성"""
        import httpx

        # SD WebUI URL (환경 변수 또는 기본값)
        sd_url = os.getenv("SD_BASE_URL", "http://127.0.0.1:7860")

        payload = {
            "prompt": prompt,
            "negative_prompt": "easynegative, lowres, bad anatomy, bad hands, cropped, worst quality",
            "steps": 25,
            "cfg_scale": 7.0,
            "sampler_name": "DPM++ 2M",
            "width": 512,
            "height": 768,
            "seed": -1,
        }

        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{sd_url}/sdapi/v1/txt2img",
                json=payload,
                timeout=120.0,
            )
            res.raise_for_status()
            data = res.json()
            return data["images"][0]

    async def _analyze_with_wd14(self, image_b64: str) -> list[dict]:
        """WD14로 태그 분석"""
        from services.validation import wd14_predict_tags
        from PIL import Image
        import io

        image_bytes = base64.b64decode(image_b64)
        image = Image.open(io.BytesIO(image_bytes))
        tags = wd14_predict_tags(image, threshold=0.35)
        return tags

    async def _analyze_with_gemini(
        self, image_b64: str, prompt: str, target_change: str
    ) -> dict:
        """Gemini Vision으로 포즈 분석"""
        from config import GEMINI_IMAGE_MODEL, GEMINI_TEXT_MODEL, gemini_client
        from google.genai import types
        from services.utils import parse_json_payload

        image_bytes = base64.b64decode(image_b64)

        instruction = f"""Analyze this chibi anime character image.

CURRENT PROMPT: {prompt}
DESIRED CHANGE: {target_change}

Describe the exact pose/action change needed in natural language for image editing.

OUTPUT (JSON only):
{{
  "current_pose": "standing with arms at sides",
  "target_pose": "{target_change}",
  "confidence": 0.85,
  "preserve_elements": ["chibi style", "aqua hair", "purple eyes", "hairclip", "t-shirt"]
}}
"""

        client = gemini_client
                    res = client.models.generate_content(
                        model=GEMINI_TEXT_MODEL,
                        contents=[
                            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                            instruction,
                        ],
                    )
        return parse_json_payload(res.text)

    async def _edit_with_gemini(
        self, image_b64: str, target_pose: str, preserve_elements: list[str]
    ) -> dict:
        """Gemini Nano Banana (2.5 Flash Image)로 이미지 편집"""
        from PIL import Image
        import io

        # Base64 → PIL
        image_bytes = base64.b64decode(image_b64)
        base_image = Image.open(io.BytesIO(image_bytes))

        # 편집 프롬프트 생성
        preserve_str = ", ".join(preserve_elements)
        edit_prompt = f"""CRITICAL: Keep the EXACT same art style and character appearance.

PRESERVE (DO NOT CHANGE):
- {preserve_str}
- Overall color palette and lighting
- Background environment

CHANGE ONLY:
- Character pose to: {target_pose}

Edit this image to match the new pose while keeping everything else identical.
"""

        # Gemini API 호출
        response = self.genai_client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[edit_prompt, base_image],
            config={
                "response_modalities": ["Image"],
            },
        )

        # 결과 → base64
        # Gemini는 raw bytes를 반환 (base64 아님)
        edited_image_data = response.candidates[0].content.parts[0].inline_data.data
        edited_b64 = base64.b64encode(edited_image_data).decode("utf-8")

        return {
            "edited_image": edited_b64,
            "cost": 0.0401,  # $0.0011 (input) + $0.039 (output)
            "method": "gemini_nano_banana",
        }

    def _evaluate(
        self,
        base_tags: list[str],
        edited_tags: list[str],
        expected_add: list[str],
        expected_remove: list[str],
    ) -> dict:
        """결과 평가"""
        base_set = set(base_tags)
        edited_set = set(edited_tags)

        added = edited_set - base_set
        removed = base_set - edited_set

        # 기대하는 태그가 추가되었는지
        add_success = sum(1 for tag in expected_add if tag in added)
        # 기대하는 태그가 제거되었는지
        remove_success = sum(1 for tag in expected_remove if tag in removed)

        total_expected = len(expected_add) + len(expected_remove)
        total_success = add_success + remove_success
        success_rate = total_success / total_expected if total_expected else 0

        verdict = "success" if success_rate >= 0.7 else "partial" if success_rate >= 0.3 else "fail"

        return {
            "added_tags": list(added)[:10],
            "removed_tags": list(removed)[:10],
            "expected_add_found": add_success,
            "expected_add_total": len(expected_add),
            "expected_remove_found": remove_success,
            "expected_remove_total": len(expected_remove),
            "success_rate": success_rate,
            "verdict": verdict,
        }

    def _save_image(self, image_b64: str, path: Path):
        """이미지 저장"""
        image_bytes = base64.b64decode(image_b64)
        path.write_bytes(image_bytes)

    def _print_result(self, result: dict):
        """결과 출력"""
        eval_data = result["evaluation"]

        verdict_map = {
            "success": "✅ SUCCESS",
            "partial": "⚠️  PARTIAL",
            "fail": "❌ FAIL",
        }

        print(f"  {verdict_map[eval_data['verdict']]}")
        print(f"  📊 Score: {eval_data['success_rate']:.1%}")
        print(f"  ➕ Added: {', '.join(eval_data['added_tags'][:5]) or 'none'}")
        print(f"  ➖ Removed: {', '.join(eval_data['removed_tags'][:5]) or 'none'}")
        print(f"  💰 Cost: ${result['cost_usd']:.4f}")

    def _generate_report(self):
        """최종 리포트 생성"""
        report_path = self.session_dir / "report.json"

        completed = [r for r in self.results if r["status"] == "completed"]
        success = sum(1 for r in completed if r["evaluation"]["verdict"] == "success")
        partial = sum(1 for r in completed if r["evaluation"]["verdict"] == "partial")
        failed = sum(1 for r in completed if r["evaluation"]["verdict"] == "fail")
        total_cost = sum(r.get("cost_usd", 0) for r in completed)

        summary = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "character": "Eureka Chibi",
            "statistics": {
                "total_tests": len(self.results),
                "completed": len(completed),
                "success": success,
                "partial": partial,
                "failed": failed,
                "success_rate": success / len(completed) if completed else 0,
                "total_cost_usd": total_cost,
            },
            "results": self.results,
        }

        report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

        # 콘솔 출력
        print(f"\n{'='*70}")
        print("📊 TEST SUMMARY")
        print(f"{'='*70}")
        print(f"Character: Eureka Chibi")
        print(f"Total Tests: {len(self.results)}")
        print(f"Completed: {len(completed)}")
        if completed:
            print(f"✅ Success: {success} ({success/len(completed)*100:.1f}%)")
            print(f"⚠️  Partial: {partial} ({partial/len(completed)*100:.1f}%)")
            print(f"❌ Failed: {failed} ({failed/len(completed)*100:.1f}%)")
        print(f"💰 Total Cost: ${total_cost:.4f}")

        # 난이도별
        print(f"\n📈 By Difficulty:")
        for difficulty in ["easy", "medium", "hard"]:
            cases = [r for r in completed if r.get("difficulty") == difficulty]
            if cases:
                succ = sum(1 for r in cases if r["evaluation"]["verdict"] == "success")
                print(f"  {difficulty.capitalize()}: {succ}/{len(cases)} ({succ/len(cases)*100:.1f}%)")

        print(f"\n📁 Report: {report_path}")
        print(f"📂 Images: {self.session_dir}")
        print(f"{'='*70}\n")


async def main():
    """메인 실행"""
    import argparse

    parser = argparse.ArgumentParser(description="Test Gemini Nano Banana with Eureka character")
    parser.add_argument("--limit", type=int, help="Limit number of tests")
    parser.add_argument("--mock", action="store_true", help="Mock mode (no API calls)")
    parser.add_argument("--test-ids", nargs="+", help="Specific test IDs to run (e.g., eureka_smile_to_frown eureka_looking_back)")
    args = parser.parse_args()

    tester = ImagenTester()
    await tester.run_all_tests(limit=args.limit, use_mock=args.mock, test_ids=args.test_ids)


if __name__ == "__main__":
    asyncio.run(main())
