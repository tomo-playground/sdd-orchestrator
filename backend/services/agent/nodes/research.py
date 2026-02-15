"""Research 노드 — Phase 2 스텁 (passthrough)."""

from __future__ import annotations

from services.agent.state import ScriptState


async def research_node(state: ScriptState) -> dict:
    """Phase 2에서 구현 예정. 현재는 passthrough."""
    return {"research_brief": None}
