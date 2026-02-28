"""Stage-Level Skip Guard — 노드가 속한 스테이지가 skip_stages에 포함되면 패스스루."""

from __future__ import annotations

from services.agent.state import ScriptState

# Core 노드 (writer, review, revise, finalize, learn)는 매핑하지 않음 — 항상 실행
_NODE_STAGE_MAP: dict[str, str] = {
    # inventory_resolve: 그래프 엣지로만 도달 → 라우팅이 가드 역할, skip_guard 불필요
    "research": "research",
    "critic": "concept",
    "concept_gate": "concept",
    "director_checkpoint": "production",
    "cinematographer": "production",
    "tts_designer": "production",
    "sound_designer": "production",
    "copyright_reviewer": "production",
    "director": "production",
    "human_gate": "production",
    "explain": "explain",
}


def should_skip(state: ScriptState, node_name: str) -> bool:
    """노드가 속한 스테이지가 skip_stages에 포함되면 True."""
    stage = _NODE_STAGE_MAP.get(node_name)
    if stage is None:
        return False
    return stage in (state.get("skip_stages") or [])
