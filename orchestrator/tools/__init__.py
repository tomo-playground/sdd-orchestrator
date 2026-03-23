"""Orchestrator MCP tools package."""

from claude_agent_sdk import create_sdk_mcp_server

from orchestrator.tools.backlog import scan_backlog
from orchestrator.tools.github import check_prs, check_workflows


def create_orchestrator_mcp_server():
    """Create an in-process MCP server with all orchestrator tools."""
    return create_sdk_mcp_server(
        name="orchestrator",
        version="1.0.0",
        tools=[scan_backlog, check_prs, check_workflows],
    )
