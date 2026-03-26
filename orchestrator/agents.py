"""Agent definitions for the SDD Orchestrator."""

from __future__ import annotations

from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions

from orchestrator.config import (
    DESIGNER_MODEL,
    DESIGNER_SYSTEM_PROMPT,
    ENABLE_AUTO_DESIGN,
    ENABLE_AUTO_RUN,
    LEAD_AGENT_MODEL,
    LEAD_AGENT_SYSTEM_PROMPT,
    MAX_AGENT_TURNS,
    PROJECT_ROOT,
)

_READ_TOOLS = [
    "mcp__orch__scan_backlog",
    "mcp__orch__check_prs",
    "mcp__orch__check_workflows",
    "mcp__orch__check_running_worktrees",
    "mcp__orch__sentry_scan",
    "mcp__orch__trigger_workflow",
    "mcp__orch__cancel_workflow",
    "mcp__orch__notify_human",
]

_WRITE_TOOLS = [
    "mcp__orch__launch_sdd_run",
    "mcp__orch__merge_pr",
    "mcp__orch__trigger_sdd_review",
]


def get_allowed_tools() -> list[str]:
    """Build the allowed_tools list based on ENABLE_AUTO_RUN."""
    tools = list(_READ_TOOLS)
    if ENABLE_AUTO_RUN:
        tools.extend(_WRITE_TOOLS)
    return tools


def create_lead_agent_options(mcp_server) -> ClaudeAgentOptions:
    """Create ClaudeAgentOptions for the Lead Agent with orchestrator tools."""
    tools = get_allowed_tools()
    if ENABLE_AUTO_DESIGN:
        tools.append("mcp__orch__run_auto_design")

    return ClaudeAgentOptions(
        model=LEAD_AGENT_MODEL,
        system_prompt=LEAD_AGENT_SYSTEM_PROMPT,
        mcp_servers={"orch": mcp_server},
        allowed_tools=tools,
        permission_mode="default",
        max_turns=MAX_AGENT_TURNS,
        cwd=PROJECT_ROOT,
    )


def create_designer_options() -> ClaudeAgentOptions:
    """Create ClaudeAgentOptions for the Designer sub-agent.

    The designer reads the codebase and produces a design.md for a task.
    """
    return ClaudeAgentOptions(
        model=DESIGNER_MODEL,
        system_prompt=DESIGNER_SYSTEM_PROMPT,
        allowed_tools=["Read", "Glob", "Grep"],
        permission_mode="default",
        max_turns=MAX_AGENT_TURNS,
        cwd=PROJECT_ROOT,
    )


def build_designer_prompt(task_dir: Path) -> str:
    """Build the user prompt for the Designer sub-agent."""
    spec_path = task_dir / "spec.md"
    spec_content = spec_path.read_text(encoding="utf-8") if spec_path.exists() else ""

    return (
        f"## Task Spec\n```markdown\n{spec_content}\n```\n\n"
        f"## Task Directory\n{task_dir}\n\n"
        f"## Project Root\n{PROJECT_ROOT}\n\n"
        "Read the codebase and write a complete design.md for this task. "
        "Output ONLY the design.md content — no preamble, no code fences around the whole output."
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
        "4. check_running_worktrees → 실행 중인 워크트리 확인\n"
        "5. sentry_scan → Sentry 에러 확인 (1시간 간격)\n"
        "6. Decision Rules에 따라 액션 실행 (launch/merge/trigger/notify)\n"
        "7. 종합 대시보드 출력"
    )


# Slack Bot은 사용자의 직접 명령이므로 ENABLE_AUTO_RUN 플래그와 무관하게
# read + write 도구를 항상 포함. Lead Agent의 _READ_TOOLS/_WRITE_TOOLS와
# 의도적으로 분리 — 도구 추가 시 양쪽 동기화 필요.
_SLACK_BOT_TOOLS = [
    "mcp__orch__scan_backlog",
    "mcp__orch__check_prs",
    "mcp__orch__check_workflows",
    "mcp__orch__check_running_worktrees",
    "mcp__orch__sentry_scan",
    "mcp__orch__launch_sdd_run",
    "mcp__orch__merge_pr",
    "mcp__orch__trigger_sdd_review",
    "mcp__orch__pause_orchestrator",
    "mcp__orch__resume_orchestrator",
    "mcp__orch__notify_human",
]


def create_slack_bot_options(mcp_server) -> ClaudeAgentOptions:
    """Create ClaudeAgentOptions for the Slack Bot Agent."""
    from orchestrator.config import (
        SLACK_BOT_AGENT_MODEL,
        SLACK_BOT_AGENT_PROMPT,
        SLACK_BOT_MAX_TURNS,
    )

    return ClaudeAgentOptions(
        model=SLACK_BOT_AGENT_MODEL,
        system_prompt=SLACK_BOT_AGENT_PROMPT,
        mcp_servers={"orch": mcp_server},
        allowed_tools=list(_SLACK_BOT_TOOLS),
        permission_mode="default",
        max_turns=SLACK_BOT_MAX_TURNS,
        cwd=PROJECT_ROOT,
    )
