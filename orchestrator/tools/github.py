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
        try:
            proc.kill()
            await proc.wait()
        except ProcessLookupError:
            pass
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

        review = pr.get("reviewDecision")
        mergeable = ci_status == "success" and review == "APPROVED"

        results.append(
            {
                "number": pr.get("number"),
                "title": pr.get("title"),
                "url": pr.get("url", ""),
                "branch": branch,
                "task_id": sp_match.group(0) if sp_match else None,
                "review": review,
                "ci_status": ci_status,
                "mergeable": mergeable,
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
    if (
        "PENDING" in statuses
        or "pending" in statuses
        or "IN_PROGRESS" in statuses
        or "QUEUED" in statuses
        or "queued" in statuses
    ):
        return "pending"
    if "" in statuses or None in statuses:
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
        return {
            "content": [{"type": "text", "text": f"GitHub error: {result['error']}"}],
            "isError": True,
        }

    summary = summarize_prs(result["data"])
    return {"content": [{"type": "text", "text": json.dumps(summary, ensure_ascii=False)}]}


async def do_merge_pr(pr_number: int) -> dict:
    """Core logic: squash-merge a PR after validating merge rules."""
    from orchestrator.rules import can_auto_merge

    # Fetch PR status first and validate merge rules
    pr_result = await _run_gh_command("pr", "view", str(pr_number), "--json", GH_PR_FIELDS)
    if "error" in pr_result:
        return _tool_error(f"Cannot check PR #{pr_number}: {pr_result['error']}")

    pr_summary = summarize_prs([pr_result["data"]])[0]

    # auto-rollback PR은 사람이 확인 후 머지
    if "auto-rollback" in pr_summary.get("labels", []):
        return _tool_error(f"PR #{pr_number} is an auto-rollback — requires human merge")

    ok, reason = can_auto_merge(pr_summary)
    if not ok:
        return _tool_error(f"Cannot merge #{pr_number}: {reason}")

    # gh pr merge outputs plain text, not JSON — use subprocess directly
    try:
        proc = await asyncio.create_subprocess_exec(
            "gh",
            "pr",
            "merge",
            str(pr_number),
            "--squash",
            "--delete-branch",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=GH_TIMEOUT)
        if proc.returncode != 0:
            return _tool_error(f"Merge failed for #{pr_number}: {stderr.decode().strip()}")
    except TimeoutError:
        return _tool_error(f"Merge timed out for #{pr_number}")
    except FileNotFoundError:
        return _tool_error("gh CLI not found")

    logger.info("Merged PR #%d", pr_number)

    # Post-merge monitoring: start Sentry error surge detection
    # Wrapped in try/except so monitoring failures never shadow a successful merge
    try:
        from orchestrator.config import SENTRY_AUTH_TOKEN

        if SENTRY_AUTH_TOKEN:
            merge_sha = await _get_merge_sha(pr_number)
            if merge_sha:
                from orchestrator.tools.rollback import start_post_merge_monitor

                start_post_merge_monitor(pr_number, merge_sha)
            else:
                logger.warning(
                    "Skipping post-merge monitor for PR #%d: merge SHA not found",
                    pr_number,
                )
        else:
            logger.warning(
                "Skipping post-merge monitor for PR #%d: SENTRY_AUTH_TOKEN not configured",
                pr_number,
            )
    except Exception:
        logger.exception("Post-merge monitor setup failed for PR #%d", pr_number)

    return {"content": [{"type": "text", "text": f"Successfully merged PR #{pr_number}"}]}


async def _get_merge_sha(pr_number: int) -> str | None:
    """Fetch the merge commit SHA for a merged PR."""
    result = await _run_gh_command("pr", "view", str(pr_number), "--json", "mergeCommit")
    if "error" in result:
        logger.warning("Failed to get merge SHA for PR #%d", pr_number)
        return None
    data = result.get("data", {})
    commit = data.get("mergeCommit") or {}
    return commit.get("oid")


def _tool_error(message: str) -> dict:
    return {
        "content": [{"type": "text", "text": message}],
        "isError": True,
    }


@tool(
    "merge_pr",
    "Squash-merge a PR that passes all quality gates",
    {
        "type": "object",
        "properties": {"pr_number": {"type": "integer", "description": "PR number to merge"}},
        "required": ["pr_number"],
    },
)
async def merge_pr(args: dict) -> dict:
    """MCP tool wrapper."""
    return await do_merge_pr(args["pr_number"])


@tool("check_workflows", "List recent GitHub Actions runs with stuck detection", {})
async def check_workflows(args: dict) -> dict:
    """MCP tool: list recent workflow runs and detect stuck ones."""
    limit = args.get("limit", GH_RUN_LIMIT)
    result = await _run_gh_command("run", "list", "--limit", str(limit), "--json", GH_RUN_FIELDS)
    if "error" in result:
        return {
            "content": [{"type": "text", "text": f"GitHub error: {result['error']}"}],
            "isError": True,
        }

    runs = result["data"]
    stuck = detect_stuck_runs(runs)
    output = {
        "runs": runs,
        "stuck": stuck,
        "total": len(runs),
        "failures": sum(1 for r in runs if r.get("conclusion") == "failure"),
    }
    return {"content": [{"type": "text", "text": json.dumps(output, ensure_ascii=False)}]}


async def do_trigger_sdd_review(pr_number: int) -> dict:
    """Core logic: trigger claude-fix workflow for a PR with changes_requested."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "gh",
            "workflow",
            "run",
            "sdd-fix.yml",
            "-f",
            f"pr_number={pr_number}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=GH_TIMEOUT)
        if proc.returncode != 0:
            return _tool_error(
                f"Failed to trigger claude-fix for #{pr_number}: {stderr.decode().strip()}"
            )
    except TimeoutError:
        return _tool_error(f"Trigger timed out for #{pr_number}")
    except FileNotFoundError:
        return _tool_error("gh CLI not found")

    logger.info("Triggered claude-fix for PR #%d", pr_number)
    return {
        "content": [
            {
                "type": "text",
                "text": f"Triggered claude-fix workflow for PR #{pr_number}",
            }
        ]
    }


@tool(
    "trigger_sdd_review",
    "Trigger claude-fix workflow for a PR with changes_requested",
    {
        "type": "object",
        "properties": {
            "pr_number": {
                "type": "integer",
                "description": "PR number to trigger review for",
            }
        },
        "required": ["pr_number"],
    },
)
async def trigger_sdd_review(args: dict) -> dict:
    """MCP tool wrapper."""
    return await do_trigger_sdd_review(args["pr_number"])


# ── GitHub Actions control tools ──────────────────────────


async def do_trigger_workflow(workflow: str, *, inputs: dict[str, str] | None = None) -> dict:
    """Core logic: trigger a GitHub Actions workflow (allowlist enforced)."""
    from orchestrator.config import GH_MONITORED_WORKFLOWS

    if workflow not in GH_MONITORED_WORKFLOWS:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "success": False,
                            "message": f"Workflow '{workflow}' not in allowed list",
                        }
                    ),
                }
            ]
        }

    cmd: list[str] = ["gh", "workflow", "run", workflow]
    if inputs:
        for key, value in inputs.items():
            cmd.extend(["-f", f"{key}={value}"])

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=GH_TIMEOUT)
        if proc.returncode != 0:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({"success": False, "message": stderr.decode().strip()}),
                    }
                ]
            }
    except TimeoutError:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"success": False, "message": "Trigger timed out"}),
                }
            ]
        }
    except FileNotFoundError:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"success": False, "message": "gh CLI not found"}),
                }
            ]
        }

    logger.info("Triggered workflow %s", workflow)
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({"success": True, "message": f"Triggered {workflow}"}),
            }
        ]
    }


@tool(
    "trigger_workflow",
    "Trigger a GitHub Actions workflow manually (allowlist enforced)",
    {
        "type": "object",
        "properties": {
            "workflow": {
                "type": "string",
                "description": "Workflow filename (e.g. sdd-review.yml)",
            },
            "inputs": {
                "type": "object",
                "description": "Workflow input parameters",
                "additionalProperties": {"type": "string"},
            },
        },
        "required": ["workflow"],
    },
)
async def trigger_workflow(args: dict) -> dict:
    """MCP tool wrapper."""
    return await do_trigger_workflow(args["workflow"], inputs=args.get("inputs"))


async def do_cancel_workflow(run_id: int) -> dict:
    """Core logic: cancel a GitHub Actions workflow run."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "gh",
            "run",
            "cancel",
            str(run_id),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=GH_TIMEOUT)
        if proc.returncode != 0:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({"success": False, "message": stderr.decode().strip()}),
                    }
                ]
            }
    except TimeoutError:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"success": False, "message": "Cancel timed out"}),
                }
            ]
        }
    except FileNotFoundError:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"success": False, "message": "gh CLI not found"}),
                }
            ]
        }

    logger.info("Cancelled workflow run %d", run_id)
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({"success": True, "message": f"Cancelled run {run_id}"}),
            }
        ]
    }


@tool(
    "cancel_workflow",
    "Cancel a stuck GitHub Actions workflow run",
    {
        "type": "object",
        "properties": {
            "run_id": {"type": "integer", "description": "Workflow run ID to cancel"},
        },
        "required": ["run_id"],
    },
)
async def cancel_workflow(args: dict) -> dict:
    """MCP tool wrapper."""
    return await do_cancel_workflow(args["run_id"])
