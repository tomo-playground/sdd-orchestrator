"""GitHub CLI wrapper tools — PR status and workflow runs."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import UTC, datetime

from claude_agent_sdk import tool

from orchestrator.config import (
    GH_PR_FIELDS,
    GH_RUN_FIELDS,
    GH_RUN_LIMIT,
    GH_TIMEOUT,
    STUCK_THRESHOLD_MINUTES,
)

logger = logging.getLogger(__name__)

SP_RE = re.compile(r"SP-\d+")


async def _run_gh_command(*args: str) -> dict:
    """Run a gh CLI command and return parsed JSON or error dict."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "gh",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=GH_TIMEOUT)

        if proc.returncode != 0:
            err_msg = stderr.decode().strip()
            logger.warning("gh command failed: %s", err_msg)
            return {"error": err_msg}

        return {"data": json.loads(stdout.decode())}
    except TimeoutError:
        logger.warning("gh command timed out (%ds)", GH_TIMEOUT)
        return {"error": f"GitHub API timeout ({GH_TIMEOUT}s)"}
    except json.JSONDecodeError as e:
        return {"error": f"JSON parse error: {e}"}
    except FileNotFoundError:
        return {"error": "gh CLI not found. Install: https://cli.github.com/"}


def summarize_prs(prs: list[dict]) -> list[dict]:
    """Summarize PR data with SP-NNN matching."""
    results = []
    for pr in prs:
        branch = pr.get("headRefName", "")
        sp_match = SP_RE.search(branch)

        # Determine CI status from statusCheckRollup
        checks = pr.get("statusCheckRollup", []) or []
        ci_status = _aggregate_check_status(checks)

        results.append(
            {
                "number": pr.get("number"),
                "title": pr.get("title"),
                "branch": branch,
                "task_id": sp_match.group(0) if sp_match else None,
                "review": pr.get("reviewDecision"),
                "ci_status": ci_status,
                "labels": [lbl.get("name", "") for lbl in (pr.get("labels") or [])],
            }
        )
    return results


def _aggregate_check_status(checks: list[dict]) -> str:
    """Aggregate status check rollup into a single status string."""
    if not checks:
        return "none"
    statuses = {c.get("conclusion") or c.get("status", "") for c in checks}
    if "FAILURE" in statuses or "failure" in statuses:
        return "failure"
    if "PENDING" in statuses or "pending" in statuses or "IN_PROGRESS" in statuses:
        return "pending"
    return "success"


def detect_stuck_runs(runs: list[dict]) -> list[dict]:
    """Detect runs that have been in_progress for too long."""
    stuck = []
    now = datetime.now(UTC)
    for run in runs:
        if run.get("status") != "in_progress":
            continue
        created = run.get("createdAt", "")
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            elapsed = (now - created_dt).total_seconds() / 60
            if elapsed > STUCK_THRESHOLD_MINUTES:
                stuck.append(
                    {
                        **run,
                        "elapsed_minutes": round(elapsed, 1),
                    }
                )
        except (ValueError, TypeError):
            continue
    return stuck


@tool("check_prs", "List open GitHub PRs with CI and review status", {})
async def check_prs(args: dict) -> dict:
    """MCP tool: list open PRs with enriched status."""
    result = await _run_gh_command("pr", "list", "--state", "open", "--json", GH_PR_FIELDS)
    if "error" in result:
        return {"content": [{"type": "text", "text": f"GitHub error: {result['error']}"}]}

    summary = summarize_prs(result["data"])
    return {"content": [{"type": "text", "text": json.dumps(summary, ensure_ascii=False)}]}


@tool("check_workflows", "List recent GitHub Actions runs with stuck detection", {})
async def check_workflows(args: dict) -> dict:
    """MCP tool: list recent workflow runs and detect stuck ones."""
    limit = args.get("limit", GH_RUN_LIMIT)
    result = await _run_gh_command("run", "list", "--limit", str(limit), "--json", GH_RUN_FIELDS)
    if "error" in result:
        return {"content": [{"type": "text", "text": f"GitHub error: {result['error']}"}]}

    runs = result["data"]
    stuck = detect_stuck_runs(runs)
    output = {
        "runs": runs,
        "stuck": stuck,
        "total": len(runs),
        "failures": sum(1 for r in runs if r.get("conclusion") == "failure"),
    }
    return {"content": [{"type": "text", "text": json.dumps(output, ensure_ascii=False)}]}
