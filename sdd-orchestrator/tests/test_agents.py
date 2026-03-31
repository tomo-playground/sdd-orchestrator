"""Unit tests for agent configuration."""

from __future__ import annotations

from unittest.mock import patch


class TestGetAllowedTools:
    def test_read_only_mode(self):
        with patch("sdd_orchestrator.agents.ENABLE_AUTO_RUN", False):
            from sdd_orchestrator.agents import get_allowed_tools

            tools = get_allowed_tools()
        assert "mcp__orch__scan_backlog" in tools
        assert "mcp__orch__check_running_worktrees" in tools
        assert "mcp__orch__launch_sdd_run" not in tools
        assert "mcp__orch__merge_pr" not in tools
        assert "mcp__orch__trigger_sdd_review" not in tools

    def test_auto_run_mode(self):
        with patch("sdd_orchestrator.agents.ENABLE_AUTO_RUN", True):
            from sdd_orchestrator.agents import get_allowed_tools

            tools = get_allowed_tools()
        assert "mcp__orch__scan_backlog" in tools
        assert "mcp__orch__launch_sdd_run" in tools
        assert "mcp__orch__merge_pr" in tools
        assert "mcp__orch__trigger_sdd_review" in tools

    def test_auto_issues_disabled(self):
        with (
            patch("sdd_orchestrator.agents.ENABLE_AUTO_RUN", False),
            patch("sdd_orchestrator.agents.ENABLE_AUTO_ISSUES", False),
        ):
            from sdd_orchestrator.agents import get_allowed_tools

            tools = get_allowed_tools()
        assert "mcp__orch__scan_issues" not in tools
        assert "mcp__orch__auto_create_task" not in tools

    def test_auto_issues_enabled(self):
        with (
            patch("sdd_orchestrator.agents.ENABLE_AUTO_RUN", False),
            patch("sdd_orchestrator.agents.ENABLE_AUTO_ISSUES", True),
        ):
            from sdd_orchestrator.agents import get_allowed_tools

            tools = get_allowed_tools()
        assert "mcp__orch__scan_issues" in tools
        assert "mcp__orch__auto_create_task" in tools
