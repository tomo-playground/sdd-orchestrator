"""Finalize 노드 — Phase 0에서는 draft를 그대로 통과시킨다.

Phase 1에서 검증/수정 로직이 추가될 예정.
"""

from __future__ import annotations

from services.agent.state import ScriptState


async def finalize_node(state: ScriptState) -> dict:
    """draft_scenes를 final_scenes로 패스스루한다."""
    return {"final_scenes": state.get("draft_scenes")}
