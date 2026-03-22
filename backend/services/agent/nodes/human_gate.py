"""Human Gate 노드 — 안전 fallback (도달 경로 없음, hands_on 폐기).

hands_on 모드 폐기로 이 노드에 도달하는 경로가 제거되었지만,
그래프 정의에 남아 있으므로 halt sentinel을 반환하여 예기치 않은 도달을 감지한다.
"""

from __future__ import annotations

from config import pipeline_logger as logger
from services.agent.state import ScriptState


async def human_gate_node(state: ScriptState) -> dict:
    """예기치 않은 도달을 경고하고 halt sentinel을 반환한다."""
    logger.warning("[LangGraph:HumanGate] unexpected reach — no active route should arrive here")
    return {"human_action": "required", "human_gate_reason": "checkpoint_fallback"}
