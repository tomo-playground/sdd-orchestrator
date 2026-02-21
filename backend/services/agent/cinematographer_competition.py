"""Cinematographer 경쟁 모듈 — 3 Lens 병렬 실행 + 스코어링 (Full 모드).

각 Lens는 서로 다른 시각적 목적(Purpose)으로 독립 실행되고,
스코어링 후 최고점 결과를 winner로 선택한다.
"""

from __future__ import annotations

import asyncio

from config import logger
from services.agent.state import ScriptState
from services.agent.tools.base import call_with_tools
from services.agent.tools.cinematographer_tools import (
    create_cinematographer_executors,
    get_cinematographer_tools,
)
from services.creative_qc import validate_visuals

CINEMATOGRAPHER_PERSPECTIVES: list[dict] = [
    {
        "role": "tension",
        "name": "Tension Lens",
        "instruction": (
            "Maximize VISUAL TENSION and conflict in every shot. "
            "Use extreme angles and high-contrast lighting to create unease and anticipation. "
            "Every frame should make the viewer feel something is about to happen."
        ),
        "techniques": [
            "dutch_angle",
            "from_below",
            "silhouette",
            "shadow",
            "high_contrast",
            "extreme_close-up",
            "backlighting",
        ],
        "temperature": 0.9,
    },
    {
        "role": "intimacy",
        "name": "Intimacy Lens",
        "instruction": (
            "Maximize EMOTIONAL CLOSENESS and vulnerability. "
            "Use intimate framing, soft lighting, and poses that reveal inner feelings. "
            "The viewer should feel like they are sharing a private moment with the character."
        ),
        "techniques": [
            "close-up",
            "depth_of_field",
            "bokeh",
            "sunlight",
            "sidelighting",
            "looking_down",
            "hand_on_chest",
        ],
        "temperature": 0.7,
    },
    {
        "role": "contrast",
        "name": "Contrast Lens",
        "instruction": (
            "Maximize VISUAL VARIETY and contrast between scenes. "
            "Each scene must look dramatically different from the previous one. "
            "Alternate between wide/close, bright/dark, static/dynamic. "
            "The visual rhythm should keep viewers engaged through constant surprise."
        ),
        "techniques": [
            "wide_shot",
            "chromatic_aberration",
            "golden_hour",
            "moonlight",
            "motion_blur",
            "bird's_eye_view",
            "from_behind",
        ],
        "temperature": 0.8,
    },
]

# 스코어링에 사용할 Danbooru 검증 태그 집합
_LIGHTING_TAGS = frozenset({"backlighting", "sunlight", "moonlight", "sidelighting", "light_rays", "golden_hour"})
_TECHNIQUE_TAGS = frozenset(
    {"depth_of_field", "bokeh", "silhouette", "lens_flare", "chromatic_aberration", "motion_blur"}
)


def _extract_scene_features(scenes: list[dict]) -> tuple[set[str], list[str], int, int, set[str]]:
    """씬 리스트에서 스코어링에 필요한 피처를 추출한다.

    Returns:
        (all_tags, cameras, lat_count, lighting_scenes, all_techniques)
    """
    all_tags: set[str] = set()
    cameras: list[str] = []
    lat_count = 0
    lighting_scenes = 0
    all_techniques: set[str] = set()

    for s in scenes:
        prompt = s.get("image_prompt", "")
        tags = {t.strip() for t in prompt.split(",") if t.strip()}
        all_tags.update(tags)
        cameras.append(s.get("camera", ""))

        if "looking_at_viewer" in tags:
            lat_count += 1
        if tags & _LIGHTING_TAGS:
            lighting_scenes += 1
        all_techniques.update(tags & _TECHNIQUE_TAGS)

    return all_tags, cameras, lat_count, lighting_scenes, all_techniques


def _calc_weighted_score(
    n: int, all_tags: set[str], cameras: list[str], lat_count: int, lighting_scenes: int, all_techniques: set[str]
) -> float:
    """추출된 피처에서 가중 점수를 계산한다."""
    tag_diversity = min(len(all_tags) / max(n * 6, 1), 1.0)
    camera_variety = min(len(set(cameras)) / max(min(3, n), 1), 1.0)

    lat_ratio = lat_count / max(n, 1)
    gaze_balance = 1.0 if lat_ratio <= 0.5 else max(0.0, 1.0 - (lat_ratio - 0.5) * 2)

    lighting_richness = lighting_scenes / max(n, 1)
    technique_variety = min(len(all_techniques) / 3, 1.0)

    changes = sum(1 for i in range(len(cameras) - 1) if cameras[i] != cameras[i + 1])
    narrative_flow = changes / max(n - 1, 1)

    return (
        tag_diversity * 0.20
        + camera_variety * 0.20
        + gaze_balance * 0.15
        + lighting_richness * 0.20
        + technique_variety * 0.15
        + narrative_flow * 0.10
    )


def score_cinematography(scenes: list[dict]) -> float:
    """씬 리스트에 대한 시네마토그래피 품질 점수를 계산한다 (0.0-1.0).

    6차원 가중 스코어: tag_diversity(0.20), camera_variety(0.20),
    gaze_balance(0.15), lighting_richness(0.20), technique_variety(0.15),
    narrative_flow(0.10).
    """
    if not scenes:
        return 0.0

    features = _extract_scene_features(scenes)
    return round(_calc_weighted_score(len(scenes), *features), 3)


_JSON_OUTPUT_INSTRUCTION = """
최종 출력은 반드시 다음 JSON 형식으로 작성하세요:
{
  "scenes": [
    {
      "order": 1,
      "text": "씬 대본",
      "visual_tags": ["tag1", "tag2", ...],
      "camera": "close-up",
      "environment": "indoors"
    },
    ...
  ]
}
"""


def _build_lens_prompt(lens: dict, base_prompt: str, director_feedback: str | None) -> str:
    """Lens별 프롬프트를 조립한다."""
    parts = [
        "당신은 쇼츠 영상의 Cinematographer Agent입니다.",
        f"당신의 렌즈: **{lens['name']}**",
        f"당신의 방향: {lens['instruction']}",
        "",
        "사용 가능한 도구:",
        "- validate_danbooru_tag: 태그가 유효한지 검증",
        "- get_character_visual_tags: 캐릭터의 비주얼 태그 조회",
        "- check_tag_compatibility: 두 태그의 충돌 여부 확인",
        "- search_similar_compositions: 유사한 분위기의 레퍼런스 태그 조합 검색",
        "",
        f"대본 정보:\n{base_prompt}",
    ]
    if director_feedback:
        parts.append(f"\n[Director 피드백]\n{director_feedback}")
    parts.append(_JSON_OUTPUT_INSTRUCTION)
    return "\n".join(parts)


async def _run_single_lens(
    lens: dict,
    state: ScriptState,
    db_session: object,
    base_prompt: str,
    director_feedback: str | None,
) -> dict:
    """단일 Lens로 Cinematographer 실행."""
    from services.agent.nodes.cinematographer import _parse_scenes  # noqa: PLC0415

    tools = get_cinematographer_tools()
    executors = create_cinematographer_executors(db_session, state)
    prompt = _build_lens_prompt(lens, base_prompt, director_feedback)
    role = lens["role"]

    try:
        response, tool_logs = await call_with_tools(
            prompt=prompt,
            tools=tools,
            tool_executors=executors,
            max_calls=10,
            trace_name=f"cinematographer_{role}",
            temperature=lens["temperature"],
        )

        scenes = _parse_scenes(response)
        if scenes is None:
            logger.warning("[CinemaCompetition] %s: JSON 파싱 실패", role)
            return {"role": role, "scenes": None, "tool_logs": tool_logs, "error": "parse_error"}

        qc = validate_visuals(scenes)
        score = score_cinematography(scenes)
        logger.info("[CinemaCompetition] %s: %d scenes, score=%.3f, qc_ok=%s", role, len(scenes), score, qc["ok"])

        return {"role": role, "scenes": scenes, "tool_logs": tool_logs, "qc": qc, "score": score, "error": None}

    except Exception as e:
        logger.warning("[CinemaCompetition] %s 실패: %s", role, e)
        return {"role": role, "scenes": None, "tool_logs": [], "error": str(e)}


_EMPTY_COMPETITION = {"scenes": None, "tool_logs": [], "qc": None, "scores": {}, "winner": None}


def _collect_valid_results(results: list) -> tuple[list[dict], dict[str, float]]:
    """병렬 실행 결과에서 유효한 것만 수집한다."""
    valid: list[dict] = []
    scores: dict[str, float] = {}
    for r in results:
        if isinstance(r, Exception):
            logger.warning("[CinemaCompetition] Lens 실행 예외: %s", r)
            continue
        if not isinstance(r, dict) or r.get("error") or not r.get("scenes"):
            role = r.get("role", "unknown") if isinstance(r, dict) else "unknown"
            logger.warning("[CinemaCompetition] %s: 유효하지 않은 결과 (skip)", role)
            continue
        valid.append(r)
        scores[r["role"]] = r["score"]
    return valid, scores


async def run_cinematographer_competition(
    state: ScriptState,
    db_session: object,
    base_prompt: str,
    director_feedback: str | None,
) -> dict:
    """3 Lens를 병렬 실행하고 최고점 결과를 반환한다."""
    tasks = [
        _run_single_lens(lens, state, db_session, base_prompt, director_feedback)
        for lens in CINEMATOGRAPHER_PERSPECTIVES
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    valid_results, all_scores = _collect_valid_results(results)

    if not valid_results:
        logger.warning("[CinemaCompetition] 모든 Lens 실패, None 반환")
        return _EMPTY_COMPETITION

    winner = max(valid_results, key=lambda x: x["score"])
    logger.info("[CinemaCompetition] Winner: %s (score=%.3f), scores=%s", winner["role"], winner["score"], all_scores)

    return {
        "scenes": winner["scenes"],
        "tool_logs": winner["tool_logs"],
        "qc": winner["qc"],
        "scores": all_scores,
        "winner": winner["role"],
    }
