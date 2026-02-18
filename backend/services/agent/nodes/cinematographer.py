"""Cinematographer 노드 — Tool-Calling Agent로 씬에 비주얼 디자인을 추가한다."""

from __future__ import annotations

import json

from langchain_core.runnables import RunnableConfig

from config import logger, template_env
from database import get_db_session
from services.agent.state import ScriptState
from services.creative_qc import validate_visuals


async def cinematographer_node(state: ScriptState, config: RunnableConfig) -> dict:
    """Tool-Calling Agent로 draft_scenes에 비주얼 디자인을 추가한다.

    LLM이 필요한 도구(태그 검증, 캐릭터 태그 조회, 호환성 체크)를 선택적으로 호출한다.
    """
    # DB 세션: config 주입 우선, 없으면 자체 생성 (Writer/Revise와 동일 패턴)
    db_session = config.get("configurable", {}).get("db") if config else None
    if db_session:
        return await _run(state, db_session)

    with get_db_session() as db:
        return await _run(state, db)


async def _run(state: ScriptState, db_session: object) -> dict:
    """Cinematographer 핵심 로직. DB 세션이 보장된 상태에서 실행."""
    from ..tools.base import call_with_tools  # noqa: PLC0415
    from ..tools.cinematographer_tools import create_cinematographer_executors, get_cinematographer_tools  # noqa: PLC0415

    # 도구 및 실행 함수 준비
    tools = get_cinematographer_tools()
    executors = create_cinematographer_executors(db_session, state)

    # LLM에게 전달할 초기 프롬프트
    scenes = state.get("draft_scenes") or []
    character_id = state.get("character_id")
    director_feedback = state.get("director_feedback")

    # 템플릿 렌더링
    tmpl = template_env.get_template("creative/cinematographer.j2")
    base_prompt = tmpl.render(scenes=scenes, character_id=character_id)

    prompt_parts = [
        "당신은 쇼츠 영상의 Cinematographer Agent입니다.",
        "각 씬에 Danbooru 태그, 카메라 앵글, 환경 설정을 추가하여 비주얼 디자인을 완성하세요.",
        "",
        "사용 가능한 도구:",
        "- validate_danbooru_tag: 태그가 유효한지 검증",
        "- get_character_visual_tags: 캐릭터의 비주얼 태그 조회 (일관성 유지)",
        "- check_tag_compatibility: 두 태그의 충돌 여부 확인",
        "- search_similar_compositions: 유사한 분위기의 레퍼런스 태그 조합 검색",
        "",
        "도구 사용 가이드:",
        "- 캐릭터 ID가 있으면 먼저 get_character_visual_tags를 호출하세요",
        "- 새로운 태그를 추가하기 전에 validate_danbooru_tag로 검증하세요",
        "- 중요한 태그 조합은 check_tag_compatibility로 충돌 여부를 확인하세요",
        "",
        f"대본 정보:\n{base_prompt}",
    ]

    if director_feedback:
        prompt_parts.append(f"\n[Director 피드백]\n{director_feedback}")

    prompt_parts.append(
        """
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
    )

    prompt = "\n".join(prompt_parts)

    # Tool-Calling 실행
    try:
        logger.info("[Cinematographer] Tool-Calling Agent 시작")
        response, tool_logs = await call_with_tools(
            prompt=prompt,
            tools=tools,
            tool_executors=executors,
            max_calls=10,  # 여러 태그 검증을 위해 10회까지 허용
            trace_name="cinematographer_tool_calling",
        )

        # JSON 파싱
        try:
            import re

            match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            json_text = match.group(1) if match else response

            result_data = json.loads(json_text)
            scenes_output = result_data.get("scenes", [])

            # QC 검증
            validation_result = validate_visuals({"scenes": scenes_output})
            if not validation_result["valid"]:
                logger.error("[Cinematographer] QC 검증 실패: %s", validation_result.get("errors"))
                return {
                    "error": f"Visual QC failed: {validation_result.get('errors')}",
                    "cinematographer_tool_logs": tool_logs,
                }

            logger.info("[Cinematographer] Tool-Calling 완료 (%d 씬, %d 도구 호출)", len(scenes_output), len(tool_logs))

            return {
                "cinematographer_result": {"scenes": scenes_output},
                "cinematographer_tool_logs": tool_logs,
            }

        except (json.JSONDecodeError, ValueError) as e:
            logger.error("[Cinematographer] JSON 파싱 실패: %s", e)
            return {
                "error": f"JSON parsing failed: {e}",
                "cinematographer_tool_logs": tool_logs,
            }

    except Exception as e:
        logger.error("[Cinematographer] Tool-Calling 실패: %s", e)
        return {
            "error": f"Cinematographer failed: {e}",
            "cinematographer_tool_logs": [],
        }
