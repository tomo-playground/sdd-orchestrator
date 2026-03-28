"""Sentry scanning tool — fetch unresolved errors, create GitHub Issues, trigger autofix."""

from __future__ import annotations

import asyncio
import json
import logging
import re

import httpx
from claude_agent_sdk import tool

from sdd_orchestrator.config import (
    GH_ISSUE_ASSIGNEE,
    GH_TIMEOUT,
    ROLLBACK_LOOKBACK_HOURS,
    SENTRY_API_BASE,
    SENTRY_AUTH_TOKEN,
    SENTRY_LOOKBACK_ALL_HOURS,
    SENTRY_ORG,
    SENTRY_PROJECTS,
    SENTRY_SCAN_LOOKBACK_HOURS,
    SENTRY_TIMEOUT_CONNECT,
    SENTRY_TIMEOUT_POOL,
    SENTRY_TIMEOUT_READ,
    SENTRY_TIMEOUT_WRITE,
)

logger = logging.getLogger(__name__)

SENTRY_ID_RE = re.compile(r"sentry-id:\s*(\d+)")


async def _fetch_sentry_issues(
    client: httpx.AsyncClient,
    project: str,
    *,
    since_hours: float = SENTRY_SCAN_LOOKBACK_HOURS,
) -> list[dict]:
    """Fetch unresolved issues from a Sentry project."""
    url = f"{SENTRY_API_BASE}/projects/{SENTRY_ORG}/{project}/issues/"
    params = {"query": "is:unresolved", "sort": "date", "limit": 25}

    try:
        resp = await client.get(url, params=params)
    except httpx.TimeoutException:
        logger.warning("Sentry API timeout for project %s", project)
        return []

    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", "5"))
        logger.warning("Sentry rate limit, retrying after %ds", retry_after)
        await asyncio.sleep(min(retry_after, 30))
        try:
            resp = await client.get(url, params=params)
        except httpx.TimeoutException:
            logger.warning("Sentry API retry timeout for project %s", project)
            return []
        if resp.status_code != 200:
            logger.warning("Sentry API retry failed: %d", resp.status_code)
            return []

    if resp.status_code == 401:
        logger.warning("Sentry auth error (401) for project %s", project)
        return []

    if resp.status_code != 200:
        logger.warning("Sentry API error %d for project %s", resp.status_code, project)
        return []

    issues = resp.json()
    # Filter by firstSeen within lookback window.
    # NOTE: This catches only NEW issues — existing issues with volume spikes
    # are detected via event count changes in fetch_error_counts() delta comparison.
    from datetime import UTC, datetime, timedelta

    cutoff = datetime.now(UTC) - timedelta(hours=since_hours)
    filtered = []
    for issue in issues:
        try:
            first_seen = datetime.fromisoformat(issue["firstSeen"].replace("Z", "+00:00"))
            if first_seen >= cutoff:
                filtered.append(issue)
        except (KeyError, ValueError):
            filtered.append(issue)
    return filtered


async def fetch_error_counts(
    client: httpx.AsyncClient,
    *,
    since_hours: float = ROLLBACK_LOOKBACK_HOURS,
) -> dict[str, int]:
    """Count active issues per Sentry project (for rollback delta comparison).

    Returns the **number of distinct issues** with ``lastSeen >= cutoff``,
    not cumulative event counts.  Using issue count avoids false-positive
    rollback triggers when a high-count existing issue enters the window.
    """
    from datetime import UTC, datetime, timedelta

    cutoff = datetime.now(UTC) - timedelta(hours=since_hours)

    counts: dict[str, int] = {}
    for project in SENTRY_PROJECTS:
        # Widen firstSeen window to 30 days so older-but-still-active issues pass through;
        # lastSeen >= cutoff is the actual inclusion gate applied below.
        issues = await _fetch_sentry_issues(client, project, since_hours=SENTRY_LOOKBACK_ALL_HOURS)
        active = 0
        for issue in issues:
            # Include if lastSeen is within the lookback window
            try:
                last_seen = datetime.fromisoformat(issue.get("lastSeen", "").replace("Z", "+00:00"))
                if last_seen < cutoff:
                    continue
            except (ValueError, TypeError):
                continue  # exclude on parse failure — avoid false positive rollback
            active += 1
        counts[project] = active
    return counts


def build_sentry_client() -> httpx.AsyncClient:
    """Create a pre-configured httpx client for Sentry API calls."""
    timeout = httpx.Timeout(
        connect=SENTRY_TIMEOUT_CONNECT,
        read=SENTRY_TIMEOUT_READ,
        write=SENTRY_TIMEOUT_WRITE,
        pool=SENTRY_TIMEOUT_POOL,
    )
    return httpx.AsyncClient(
        timeout=timeout,
        headers={"Authorization": f"Bearer {SENTRY_AUTH_TOKEN}"},
    )


async def _fetch_latest_stacktrace(client: httpx.AsyncClient, issue_id: str) -> str:
    """Fetch the latest event's stacktrace for a Sentry issue."""
    url = f"{SENTRY_API_BASE}/issues/{issue_id}/events/latest/"

    try:
        resp = await client.get(url)
    except httpx.TimeoutException:
        logger.warning("Stacktrace fetch timeout for issue %s", issue_id)
        return ""

    if resp.status_code != 200:
        return ""

    event = resp.json()
    entries = event.get("entries", [])
    for entry in entries:
        if entry.get("type") == "exception":
            values = entry.get("data", {}).get("values", [])
            parts = []
            for val in values:
                exc_type = val.get("type", "")
                exc_value = val.get("value", "")
                frames = val.get("stacktrace", {}).get("frames", [])
                frame_strs = []
                for f in frames[-5:]:
                    fn = f.get("filename", "?")
                    ln = f.get("lineNo", "?")
                    func = f.get("function", "?")
                    frame_strs.append(f"  {fn}:{ln} in {func}")
                parts.append(f"{exc_type}: {exc_value}\n" + "\n".join(frame_strs))
            return "\n\n".join(parts)
    return ""


async def _get_existing_sentry_ids() -> set[str]:
    """Get set of sentry issue IDs already tracked in GitHub Issues."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "gh",
            "issue",
            "list",
            "--label",
            "sentry",
            "--state",
            "all",
            "--limit",
            "500",
            "--json",
            "title,body",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=GH_TIMEOUT)
        if proc.returncode != 0:
            return set()

        issues = json.loads(stdout.decode())
        ids: set[str] = set()
        for issue in issues:
            body = issue.get("body", "")
            match = SENTRY_ID_RE.search(body)
            if match:
                ids.add(match.group(1))
        return ids
    except (TimeoutError, json.JSONDecodeError, FileNotFoundError):
        logger.warning("Failed to fetch existing sentry IDs from GitHub")
        return set()


async def _create_github_issue(project: str, issue_data: dict, stacktrace: str) -> int | None:
    """Create a GitHub Issue for a Sentry error."""
    title = f"[Sentry/{project}] {issue_data['title']}"
    body = (
        f"**Sentry Issue**: {issue_data.get('permalink', '')}\n"
        f"**Level**: {issue_data.get('level', 'error')}\n"
        f"**Culprit**: {issue_data.get('culprit', 'unknown')}\n"
        f"**Count**: {issue_data.get('count', '?')}\n"
        f"**First Seen**: {issue_data.get('firstSeen', '?')}\n\n"
        f"sentry-id: {issue_data['id']}\n\n"
        f"## Stacktrace\n```\n{stacktrace or 'No stacktrace available'}\n```"
    )

    try:
        proc = await asyncio.create_subprocess_exec(
            "gh",
            "issue",
            "create",
            "--title",
            title,
            "--body",
            body,
            "--label",
            "sentry",
            "--label",
            "bug",
            "--assignee",
            GH_ISSUE_ASSIGNEE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=GH_TIMEOUT)
        if proc.returncode != 0:
            logger.warning("Failed to create GitHub Issue: %s", stderr.decode().strip())
            return None

        # Parse issue number from URL (e.g., "https://github.com/.../issues/42")
        url = stdout.decode().strip()
        match = re.search(r"/issues/(\d+)", url)
        return int(match.group(1)) if match else None
    except (TimeoutError, FileNotFoundError):
        logger.warning("Failed to create GitHub Issue (timeout or gh not found)")
        return None


async def _trigger_autofix(issue_number: int) -> bool:
    """Trigger sentry-autofix workflow for a GitHub Issue."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "gh",
            "workflow",
            "run",
            "sentry-autofix.yml",
            "-f",
            f"issue_number={issue_number}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=GH_TIMEOUT)
        if proc.returncode != 0:
            logger.warning("Failed to trigger autofix: %s", stderr.decode().strip())
            return False
        return True
    except (TimeoutError, FileNotFoundError):
        logger.warning("Failed to trigger autofix (timeout or gh not found)")
        return False


async def do_sentry_scan() -> dict:
    """Core logic: scan all Sentry projects for new unresolved errors."""
    if not SENTRY_AUTH_TOKEN:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"error": "SENTRY_AUTH_TOKEN not configured"}),
                }
            ]
        }

    stats = {"new": 0, "skipped": 0, "created": 0, "triggered": 0}
    existing_ids = await _get_existing_sentry_ids()

    async with build_sentry_client() as client:
        for project in SENTRY_PROJECTS:
            issues = await _fetch_sentry_issues(client, project)
            for issue in issues:
                stats["new"] += 1
                if issue["id"] in existing_ids:
                    stats["skipped"] += 1
                    continue

                stacktrace = await _fetch_latest_stacktrace(client, issue["id"])
                issue_number = await _create_github_issue(project, issue, stacktrace)
                if issue_number:
                    stats["created"] += 1
                    if await _trigger_autofix(issue_number):
                        stats["triggered"] += 1

    logger.info("Sentry scan complete: %s", stats)
    return {"content": [{"type": "text", "text": json.dumps(stats)}]}


@tool(
    "sentry_scan",
    "Scan Sentry for unresolved errors, create GitHub Issues, trigger autofix",
    {},
)
async def sentry_scan(args: dict) -> dict:
    """MCP tool wrapper."""
    return await do_sentry_scan()
