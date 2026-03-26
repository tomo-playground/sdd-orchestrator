"""Orchestrator MCP tools package."""

from claude_agent_sdk import create_sdk_mcp_server

from orchestrator.config import ENABLE_AUTO_DESIGN, ENABLE_AUTO_RUN
from orchestrator.tools.backlog import scan_backlog
from orchestrator.tools.github import (
    cancel_workflow,
    check_prs,
    check_workflows,
    merge_pr,
    trigger_sdd_review,
    trigger_workflow,
)
from orchestrator.tools.notify import notify_human
from orchestrator.tools.sentry import sentry_scan
from orchestrator.tools.slack_bot import pause_orchestrator, resume_orchestrator
from orchestrator.tools.worktree import check_running_worktrees, launch_sdd_run


def create_orchestrator_mcp_server():
    """Create an in-process MCP server with all orchestrator tools."""
    tools = [
        scan_backlog,
        check_prs,
        check_workflows,
        check_running_worktrees,
        sentry_scan,
        trigger_workflow,
        cancel_workflow,
        notify_human,
        pause_orchestrator,
        resume_orchestrator,
    ]
    if ENABLE_AUTO_RUN:
        tools.extend([launch_sdd_run, merge_pr, trigger_sdd_review])

    if ENABLE_AUTO_DESIGN:
        from orchestrator.tools.design import run_auto_design

        tools.append(run_auto_design)

    return create_sdk_mcp_server(
        name="orchestrator",
        version="1.0.0",
        tools=tools,
    )
