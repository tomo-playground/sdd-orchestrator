"""Lead Agent definition for the SDD Orchestrator."""

from __future__ import annotations

from claude_agent_sdk import ClaudeAgentOptions

from orchestrator.config import (
    LEAD_AGENT_MODEL,
    LEAD_AGENT_SYSTEM_PROMPT,
    MAX_AGENT_TURNS,
    PROJECT_ROOT,
)


def create_lead_agent_options(mcp_server) -> ClaudeAgentOptions:
    """Create ClaudeAgentOptions for the Lead Agent with orchestrator tools."""
    return ClaudeAgentOptions(
        model=LEAD_AGENT_MODEL,
        system_prompt=LEAD_AGENT_SYSTEM_PROMPT,
        mcp_servers={"orch": mcp_server},
        allowed_tools=[
            "mcp__orch__scan_backlog",
            "mcp__orch__check_prs",
            "mcp__orch__check_workflows",
        ],
        permission_mode="default",
        max_turns=MAX_AGENT_TURNS,
        cwd=PROJECT_ROOT,
    )


def build_cycle_prompt(cycle_number: int, previous_summary: str | None) -> str:
    """Build the user prompt for a cycle."""
    prev = previous_summary or "첫 사이클입니다."
    return (
        f"사이클 #{cycle_number} 점검을 시작합니다.\n"
        f"이전 사이클 요약: {prev}\n\n"
        "도구를 사용하여:\n"
        "1. scan_backlog → 백로그 + 태스크 상태 확인\n"
        "2. check_prs → 열린 PR 상태 확인\n"
        "3. check_workflows → GitHub Actions 상태 확인\n"
        "4. 종합 판단 → 대시보드 출력 + 다음 행동 제안"
    )
