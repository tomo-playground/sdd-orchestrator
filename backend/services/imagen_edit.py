"""Gemini Nano Banana 이미지 편집 서비스

Google AI Studio의 gemini-2.5-flash-image 모델을 사용하여
생성된 이미지의 포즈/표정/시선을 편집합니다.

주요 기능:
- 포즈 편집 (standing → sitting, waving 등)
- 표정 편집 (smile → frown, surprised 등)
- 시선 편집 (front → looking_back 등)
- 캐릭터 얼굴/화풍 완벽 보존
"""
import base64
import io
import logging
from typing import Literal

from google import genai
from google.genai import types
from PIL import Image

from config import GEMINI_TEXT_MODEL, gemini_client
from services.image import decode_data_url
from services.utils import parse_json_payload

logger = logging.getLogger(__name__)

EditType = Literal["pose", "expression", "gaze", "framing", "hands"]


class ImagenEditService:
    """Gemini Nano Banana 이미지 편집 서비스"""

    def __init__(self):
        """서비스 초기화"""
        self.client = self._init_gemini_client()

    def _init_gemini_client(self) -> genai.Client:
        """Gemini API 클라이언트 초기화"""
        try:
            client = gemini_client
            logger.info("✅ Gemini Nano Banana API initialized")
            return client
        except Exception as e:
            logger.error(f"❌ Gemini API initialization failed: {e}")
            raise

    async def analyze_edit_needed(
        self, image_b64: str, original_prompt: str, target_change: str
    ) -> dict:
        """Gemini Vision으로 편집 계획 분석

        Args:
            image_b64: Base64 인코딩된 이미지 (Data URL 또는 raw base64)
            original_prompt: 원본 프롬프트
            target_change: 목표 변경사항 (예: "sitting on chair")

        Returns:
            {
                "current_state": "standing with arms at sides",
                "target_state": "sitting on chair with hands on lap",
                "confidence": 0.85,
                "preserve_elements": ["chibi style", "aqua hair", ...],
                "edit_type": "pose"
            }
        """
        try:
            logger.info(f"📥 Analyzing image... (length: {len(image_b64)} chars)")
            logger.info(f"   First 50 chars: {image_b64[:50]}...")

            image_bytes = decode_data_url(image_b64)
            logger.info(f"✅ Image decoded successfully ({len(image_bytes)} bytes)")

            instruction = f"""Analyze this anime character image for editing.

CURRENT PROMPT: {original_prompt}
DESIRED CHANGE: {target_change}

Describe what needs to change and what must be preserved.

Determine the edit_type by analyzing what aspect needs to change:
- Use "pose" for body position changes (sitting, standing, jumping)
- Use "expression" for facial expression changes (smiling, frowning, surprised)
- Use "gaze" for viewing direction changes (looking at viewer, looking back)
- Use "framing" for camera angle/framing changes (close-up, full-body)
- Use "hands" for hand pose/gesture changes

For the change "{target_change}", the edit_type is most likely "pose".

OUTPUT (JSON only, NO explanations):
{{
  "current_state": "describe current state",
  "target_state": "{target_change}",
  "confidence": 0.85,
  "preserve_elements": ["art style", "hair color", "eye color", "clothing"],
  "edit_type": "pose"
}}

CRITICAL: Return ONLY valid JSON. The edit_type value must be a single word from this list: pose, expression, gaze, framing, hands
"""

            res = await self.client.aio.models.generate_content(
                model=GEMINI_TEXT_MODEL,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    instruction,
                ],
            )

            result = parse_json_payload(res.text)

            # Validate and fix edit_type (CRITICAL: must be one of the valid literals)
            valid_types: list[EditType] = ["pose", "expression", "gaze", "framing", "hands"]
            original_type = result.get("edit_type", "")

            if original_type not in valid_types:
                # Fallback: guess from target_change
                target_lower = target_change.lower()
                if any(word in target_lower for word in ["sit", "stand", "jump", "kneel", "앉", "서", "점프", "일어", "서있"]):
                    result["edit_type"] = "pose"
                elif any(word in target_lower for word in ["smile", "frown", "surprised", "angry", "웃", "찡그", "놀란", "화난", "표정"]):
                    result["edit_type"] = "expression"
                elif any(word in target_lower for word in ["look", "gaze", "보", "시선", "쳐다", "바라"]):
                    result["edit_type"] = "gaze"
                elif any(word in target_lower for word in ["close", "full", "zoom", "클로즈", "전신"]):
                    result["edit_type"] = "framing"
                elif any(word in target_lower for word in ["hand", "finger", "손", "손가락"]):
                    result["edit_type"] = "hands"
                else:
                    result["edit_type"] = "pose"  # Default to pose

                logger.warning(f"⚠️ Invalid edit_type '{original_type}', corrected to '{result['edit_type']}'")

            logger.info(f"✅ Vision analysis complete: {result['edit_type']}")
            return result

        except Exception as e:
            logger.error(f"❌ Vision analysis failed: {e}")
            raise

    async def edit_image(
        self,
        image_b64: str,
        target_change: str,
        preserve_elements: list[str],
        edit_type: EditType = "pose",
    ) -> dict:
        """Gemini Nano Banana로 이미지 편집

        Args:
            image_b64: Base64 인코딩된 원본 이미지 (Data URL 또는 raw base64)
            target_change: 목표 변경사항
            preserve_elements: 보존할 요소 리스트
            edit_type: 편집 타입 (pose/expression/gaze 등)

        Returns:
            {
                "edited_image": "base64 string",
                "cost_usd": 0.0401,
                "method": "gemini_nano_banana",
                "edit_type": "pose"
            }
        """
        try:
            # Data URL → PIL Image
            image_bytes = decode_data_url(image_b64)
            base_image = Image.open(io.BytesIO(image_bytes))

            # 편집 타입별 프롬프트 생성
            edit_prompt = self._generate_edit_prompt(
                target_change, preserve_elements, edit_type
            )

            logger.info(f"🎨 Editing image with Gemini Nano Banana ({edit_type})...")

            # Gemini API 호출 (async)
            response = await self.client.aio.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[edit_prompt, base_image],
                config={
                    "response_modalities": ["Image"],
                },
            )

            # 결과 추출 → base64
            edited_image_data = response.candidates[0].content.parts[0].inline_data.data
            edited_b64 = base64.b64encode(edited_image_data).decode("utf-8")

            logger.info("✅ Image editing complete (cost: $0.0401)")

            return {
                "edited_image": edited_b64,
                "cost_usd": 0.0401,  # $0.0011 (input) + $0.039 (output)
                "method": "gemini_nano_banana",
                "edit_type": edit_type,
            }

        except Exception as e:
            logger.error(f"❌ Image editing failed: {e}")
            raise

    async def enhance_image(self, image_b64: str) -> dict:
        """Gemini로 캐릭터 프리뷰 이미지 고품질 보정

        캐릭터 identity/스타일/포즈를 보존하면서 선화/색감/디테일만 향상합니다.

        Args:
            image_b64: Base64 인코딩된 이미지 (Data URL 또는 raw base64)

        Returns:
            {"enhanced_image": "base64 string", "cost_usd": 0.0401}
        """
        try:
            image_bytes = decode_data_url(image_b64)
            base_image = Image.open(io.BytesIO(image_bytes))

            prompt = (
                "Enhance this anime character illustration while strictly preserving "
                "the character's identity, pose, outfit, art style, and composition. "
                "Improve ONLY: line art clarity, color vibrancy, shading quality, "
                "and fine details (eyes, hair strands, fabric texture). "
                "Do NOT change the character's face, body proportions, clothing design, "
                "or background. Output a single improved image."
            )

            logger.info("✨ Enhancing image with Gemini...")
            response = await self.client.aio.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[prompt, base_image],
                config={"response_modalities": ["Image"]},
            )

            enhanced_data = response.candidates[0].content.parts[0].inline_data.data
            enhanced_b64 = base64.b64encode(enhanced_data).decode("utf-8")

            logger.info("✅ Image enhance complete (cost: $0.0401)")
            return {"enhanced_image": enhanced_b64, "cost_usd": 0.0401}

        except Exception as e:
            logger.error(f"❌ Image enhance failed: {e}")
            raise

    def _generate_edit_prompt(
        self, target_change: str, preserve_elements: list[str], edit_type: EditType
    ) -> str:
        """편집 타입별 프롬프트 생성"""
        preserve_str = ", ".join(preserve_elements)

        # 공통 보존 지침
        base_preservation = f"""CRITICAL: Keep the EXACT same art style and character appearance.

PRESERVE (DO NOT CHANGE):
- {preserve_str}
- Overall color palette and lighting
- Background environment
"""

        # 편집 타입별 지침
        if edit_type == "pose":
            change_instruction = f"""CHANGE ONLY:
- Character pose/body position to: {target_change}
- Adjust limbs and body naturally for the new pose"""

        elif edit_type == "expression":
            change_instruction = f"""CHANGE ONLY:
- Facial expression to: {target_change}
- Eyes, mouth, and face shape to match the new emotion
- Keep all other facial features identical"""

        elif edit_type == "gaze":
            change_instruction = f"""CHANGE ONLY:
- Gaze direction/viewing angle to: {target_change}
- Head/body orientation as needed for the new angle
- Maintain character identity from the new angle"""

        elif edit_type == "framing":
            change_instruction = f"""CHANGE ONLY:
- Camera framing/composition to: {target_change}
- Adjust visible body parts accordingly
- Maintain consistent character appearance"""

        elif edit_type == "hands":
            change_instruction = f"""CHANGE ONLY:
- Hand pose/gesture to: {target_change}
- Ensure correct anatomy (5 fingers, natural positioning)
- Keep arms and rest of body consistent"""

        else:
            # Default (general)
            change_instruction = f"""CHANGE ONLY:
- {target_change}"""

        return f"{base_preservation}\n{change_instruction}\n\nEdit this image carefully while preserving the character's identity."

    async def suggest_edit_from_prompt(
        self, image_b64: str, original_prompt_ko: str
    ) -> dict:
        """한국어 프롬프트와 이미지를 비교해 자동 제안 생성

        Args:
            image_b64: Base64 인코딩된 이미지 (Data URL 또는 raw base64)
            original_prompt_ko: 한국어 프롬프트 (예: "1girl, sitting, indoors, smiling")

        Returns:
            {
                "has_mismatch": True/False,
                "suggestions": [
                    {
                        "issue": "포즈 불일치",
                        "description": "프롬프트에는 'sitting'이 있지만 이미지는 서 있습니다",
                        "target_change": "의자에 앉은 포즈로 변경",
                        "confidence": 0.85,
                        "edit_type": "pose"
                    }
                ],
                "cost_usd": 0.0003
            }
        """
        try:
            logger.info(f"📥 Suggesting edits for prompt: {original_prompt_ko[:50]}...")

            image_bytes = decode_data_url(image_b64)
            logger.info(f"✅ Image decoded successfully ({len(image_bytes)} bytes)")

            instruction = f"""Analyze this anime character image and compare it with the prompt.

PROMPT: {original_prompt_ko}

Find ANY mismatches between the prompt and the actual image.

Focus on these aspects:
- **Pose**: sitting, standing, jumping, lying down, etc.
- **Expression**: smiling, frowning, surprised, neutral, etc.
- **Gaze**: looking at viewer, looking back, looking away, etc.
- **Hands**: hand positions, gestures (waving, peace sign, etc.)
- **Framing**: close-up, cowboy shot, full-body, etc.

For EACH mismatch found, determine the edit_type:
- Use "pose" for body position mismatches
- Use "expression" for facial expression mismatches
- Use "gaze" for viewing direction mismatches
- Use "framing" for camera angle/framing mismatches
- Use "hands" for hand pose/gesture mismatches

OUTPUT (JSON only, NO explanations):
{{
  "has_mismatch": true,
  "suggestions": [
    {{
      "issue": "포즈 불일치",
      "description": "프롬프트에는 'sitting'이 있지만 이미지는 서 있습니다",
      "target_change": "의자에 앉은 포즈로 변경",
      "confidence": 0.85,
      "edit_type": "pose"
    }}
  ]
}}

If NO mismatches are found:
{{
  "has_mismatch": false,
  "suggestions": []
}}

CRITICAL: Return ONLY valid JSON. Each edit_type must be one of: pose, expression, gaze, framing, hands
"""

            res = await self.client.aio.models.generate_content(
                model=GEMINI_TEXT_MODEL,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    instruction,
                ],
            )

            result = parse_json_payload(res.text)

            # Validate edit_type for each suggestion
            valid_types: list[EditType] = ["pose", "expression", "gaze", "framing", "hands"]
            if result.get("has_mismatch") and result.get("suggestions"):
                for suggestion in result["suggestions"]:
                    if suggestion.get("edit_type") not in valid_types:
                        # Default to pose if invalid
                        logger.warning(f"⚠️ Invalid edit_type '{suggestion.get('edit_type')}', defaulting to 'pose'")
                        suggestion["edit_type"] = "pose"

            result["cost_usd"] = 0.0003  # Vision API cost

            logger.info(f"✅ Edit suggestions generated: {len(result.get('suggestions', []))} suggestions")
            return result

        except Exception as e:
            logger.error(f"❌ Suggest edit failed: {e}")
            raise

    async def edit_with_analysis(
        self, image_b64: str, original_prompt: str, target_change: str
    ) -> dict:
        """자동 분석 후 편집 (all-in-one)

        Args:
            image_b64: Base64 인코딩된 이미지
            original_prompt: 원본 프롬프트
            target_change: 목표 변경사항

        Returns:
            {
                "edited_image": "base64",
                "cost_usd": 0.0404,
                "analysis": {...},
                "edit_result": {...}
            }
        """
        # Step 1: Vision 분석
        analysis = await self.analyze_edit_needed(
            image_b64, original_prompt, target_change
        )

        # Step 2: 편집 실행
        edit_result = await self.edit_image(
            image_b64=image_b64,
            target_change=analysis["target_state"],
            preserve_elements=analysis["preserve_elements"],
            edit_type=analysis["edit_type"],
        )

        # 총 비용 계산
        total_cost = 0.0003 + edit_result["cost_usd"]  # Vision + Edit

        return {
            "edited_image": edit_result["edited_image"],
            "cost_usd": total_cost,
            "analysis": analysis,
            "edit_result": edit_result,
        }


# 싱글톤 인스턴스
_imagen_service = None


def _infer_edit_type_from_missing_tags(missing_tags: list[str]) -> EditType:
    """누락된 태그에서 편집 타입 추론

    Args:
        missing_tags: WD14 검증에서 누락된 태그 목록

    Returns:
        EditType: pose, expression, gaze, framing, hands

    Examples:
        ["sitting", "chair"] → "pose"
        ["smiling", "happy"] → "expression"
        ["looking_at_viewer"] → "gaze"
        ["close-up", "cowboy_shot"] → "framing"
        ["peace_sign", "waving"] → "hands"
    """
    # 우선순위: pose > expression > gaze > hands > framing
    tag_lower = " ".join(missing_tags).lower()

    # Pose keywords (body position)
    if any(kw in tag_lower for kw in [
        "sit", "stand", "jump", "kneel", "lying", "crouch", "lean",
        "앉", "서", "점프", "무릎", "누워", "서있"
    ]):
        return "pose"

    # Expression keywords (facial emotion)
    if any(kw in tag_lower for kw in [
        "smile", "smiling", "frown", "surprised", "angry", "sad", "happy",
        "웃", "찡그", "놀란", "화난", "슬픈", "표정"
    ]):
        return "expression"

    # Gaze keywords (viewing direction)
    if any(kw in tag_lower for kw in [
        "look", "looking", "gaze", "viewer", "back", "away",
        "보", "시선", "쳐다", "바라"
    ]):
        return "gaze"

    # Hands keywords (hand gestures)
    if any(kw in tag_lower for kw in [
        "hand", "hands", "finger", "wave", "waving", "peace", "pointing",
        "손", "손가락", "흔들", "가리"
    ]):
        return "hands"

    # Framing keywords (camera angle)
    if any(kw in tag_lower for kw in [
        "close", "full", "shot", "cowboy", "upper_body", "portrait",
        "클로즈", "전신", "반신"
    ]):
        return "framing"

    # Default to pose if no specific keywords found
    return "pose"


def _generate_target_change(missing_tags: list[str], edit_type: EditType) -> str:
    """누락 태그 → 자연어 변경사항 생성

    Args:
        missing_tags: 누락된 태그 목록
        edit_type: 편집 타입

    Returns:
        자연어 변경 지시 (Gemini가 이해할 수 있는 형태)

    Examples:
        ["sitting", "chair"] + pose → "sitting on chair"
        ["smiling"] + expression → "smiling with bright expression"
        ["looking_at_viewer"] + gaze → "looking directly at viewer"
    """
    if not missing_tags:
        return "adjust to match prompt"

    # Join tags with natural spacing
    tags_str = " ".join(missing_tags)

    if edit_type == "pose":
        # Pose: use tags directly (Gemini will infer natural positioning)
        return tags_str
    elif edit_type == "expression":
        # Expression: emphasize emotion
        return f"{tags_str} expression" if "expression" not in tags_str else tags_str
    elif edit_type == "gaze":
        # Gaze: keep simple
        return tags_str
    elif edit_type == "hands":
        # Hands: specify gesture
        return f"hand gesture: {tags_str}" if "hand" not in tags_str else tags_str
    else:
        # Framing: use tags directly
        return tags_str


async def auto_edit_with_gemini(
    image_b64: str,
    original_prompt: str,
    match_rate: float,
    missing_tags: list[str]
) -> dict:
    """Match Rate가 낮을 때 자동으로 Gemini 편집 실행

    Args:
        image_b64: Base64 인코딩된 이미지 (Data URL 또는 raw base64)
        original_prompt: 원본 프롬프트
        match_rate: WD14 Match Rate (0.0~1.0)
        missing_tags: 누락된 태그 목록

    Returns:
        {
            "edited_image": "base64",
            "cost_usd": 0.0404,
            "edit_type": "pose",
            "auto_generated": True,
            "original_match_rate": 0.65,
            "analysis": {...}
        }

    Raises:
        Exception: Gemini API 실패 시
    """
    try:
        logger.info(
            f"🤖 [Auto Edit] Starting (match_rate={match_rate:.2f}, missing_tags={len(missing_tags)})"
        )

        # Step 1: 실패 태그 분석 → 편집 타입 추론
        edit_type = _infer_edit_type_from_missing_tags(missing_tags)
        logger.info(f"   Inferred edit_type: {edit_type}")

        # Step 2: 누락 태그 → 자연어 target_change 생성
        target_change = _generate_target_change(missing_tags, edit_type)
        logger.info(f"   Generated target_change: {target_change}")

        # Step 3: Gemini 편집 실행 (ImagenEditService 재사용)
        service = get_imagen_service()
        result = await service.edit_with_analysis(
            image_b64=image_b64,
            original_prompt=original_prompt,
            target_change=target_change
        )

        # Step 4: 자동 생성 플래그 추가
        result["auto_generated"] = True
        result["original_match_rate"] = match_rate
        result["inferred_edit_type"] = edit_type
        result["generated_target_change"] = target_change

        logger.info(
            f"✅ [Auto Edit] Success (type={edit_type}, cost=${result['cost_usd']:.4f})"
        )

        return result

    except Exception as e:
        logger.error(f"❌ [Auto Edit] Failed: {e}")
        raise


def get_imagen_service() -> ImagenEditService:
    """ImagenEditService 싱글톤 인스턴스 반환"""
    global _imagen_service
    if _imagen_service is None:
        _imagen_service = ImagenEditService()
    return _imagen_service
