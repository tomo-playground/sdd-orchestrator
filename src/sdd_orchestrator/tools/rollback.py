"""Post-merge rollback monitor — detect Sentry error surges and create revert PRs."""

from __future__ import annotations

import asyncio
import logging
import re
import tempfile

from sdd_orchestrator.config import (
    GH_ISSUE_ASSIGNEE,
    GH_PR_CREATE_TIMEOUT,
    GH_TIMEOUT,
    GIT_BOT_EMAIL,
    GIT_BOT_NAME,
    GIT_CLONE_TIMEOUT,
    REPO_FULL_NAME,
    REPO_SSH_URL,
    ROLLBACK_CHECK_INTERVAL,
    ROLLBACK_ERROR_THRESHOLD,
    ROLLBACK_LOOKBACK_HOURS,
    ROLLBACK_MAX_FETCH_FAILURES,
    ROLLBACK_MONITOR_DURATION,
)

logger = logging.getLogger(__name__)

# Strong references to prevent GC of background tasks
_active_monitors: set[asyncio.Task] = set()


def start_post_merge_monitor(pr_number: int, merge_sha: str) -> None:
    """Launch a background monitor task for a merged PR.

    Non-blocking — creates an asyncio task and returns immediately.
    """
    task = asyncio.create_task(
        _monitor_loop(pr_number, merge_sha),
        name=f"rollback-monitor-PR-{pr_number}",
    )
    _active_monitors.add(task)
    task.add_done_callback(_active_monitors.discard)
    logger.info("Started post-merge monitor for PR #%d (sha=%s)", pr_number, merge_sha[:8])


def _check_surge(baseline: dict[str, int], current: dict[str, int]) -> tuple[bool, int]:
    """Pure calculation: compare error counts against threshold."""
    delta = sum(current.values()) - sum(baseline.values())
    return (delta >= ROLLBACK_ERROR_THRESHOLD, delta)


async def _monitor_loop(pr_number: int, merge_sha: str) -> None:
    """Monitor Sentry errors for ROLLBACK_MONITOR_DURATION after merge."""
    from sdd_orchestrator.tools.sentry import build_sentry_client, fetch_error_counts

    # Lazy import to avoid circular dependency at module load
    state = _get_state_store()
    if state and state.has_rollback(pr_number):
        logger.info("Rollback already exists for PR #%d, skipping monitor", pr_number)
        return

    rollback_id = (
        state.record_rollback(pr_number, error_count=0, baseline_count=0) if state else None
    )
    # record_rollback returns None on duplicate (UNIQUE constraint)
    if state and rollback_id is None:
        logger.info("Duplicate rollback insert for PR #%d, skipping monitor", pr_number)
        return

    max_checks = ROLLBACK_MONITOR_DURATION // ROLLBACK_CHECK_INTERVAL
    fetch_failure_count = 0

    try:
        async with build_sentry_client() as client:
            baseline = await fetch_error_counts(client, since_hours=ROLLBACK_LOOKBACK_HOURS)
            baseline_total = sum(baseline.values())

            if rollback_id and state:
                state.update_rollback_baseline(rollback_id, baseline_total)

            logger.info("PR #%d baseline: %d errors (%s)", pr_number, baseline_total, baseline)

            for i in range(max_checks):
                await asyncio.sleep(ROLLBACK_CHECK_INTERVAL)
                try:
                    current = await fetch_error_counts(client, since_hours=ROLLBACK_LOOKBACK_HOURS)
                    fetch_failure_count = 0  # reset on success
                except Exception:
                    fetch_failure_count += 1
                    logger.warning(
                        "PR #%d check %d/%d: Sentry fetch failed (%d/%d)",
                        pr_number,
                        i + 1,
                        max_checks,
                        fetch_failure_count,
                        ROLLBACK_MAX_FETCH_FAILURES,
                    )
                    if fetch_failure_count >= ROLLBACK_MAX_FETCH_FAILURES:
                        logger.error(
                            "PR #%d: Sentry fetch failed %d times — marking monitor_failed",
                            pr_number,
                            fetch_failure_count,
                        )
                        if rollback_id and state:
                            state.update_rollback_status(rollback_id, "monitor_failed")
                        return
                    continue

                is_surge, delta = _check_surge(baseline, current)
                logger.info(
                    "PR #%d check %d/%d: delta=%d (threshold=%d)",
                    pr_number,
                    i + 1,
                    max_checks,
                    delta,
                    ROLLBACK_ERROR_THRESHOLD,
                )

                if is_surge:
                    logger.warning("PR #%d SURGE DETECTED: +%d errors", pr_number, delta)
                    if rollback_id and state:
                        state.update_rollback_surge(rollback_id, sum(current.values()))

                    await _handle_surge(pr_number, merge_sha, delta, rollback_id)
                    return

        # Monitoring complete with no surge
        if rollback_id and state:
            state.update_rollback_status(rollback_id, "no_surge")
        logger.info("PR #%d monitoring complete — no surge detected", pr_number)

    except asyncio.CancelledError:
        logger.info("PR #%d monitor cancelled", pr_number)
        if rollback_id and state:
            state.update_rollback_status(rollback_id, "cancelled")
        raise
    except Exception:
        logger.exception("PR #%d monitor failed", pr_number)
        if rollback_id and state:
            state.update_rollback_status(rollback_id, "monitor_failed")


async def _handle_surge(
    pr_number: int, merge_sha: str, delta: int, rollback_id: int | None
) -> None:
    """Handle a detected error surge: create revert PR + notify."""
    from sdd_orchestrator.tools.notify import do_notify_human

    state = _get_state_store()
    revert_pr = await _create_revert_pr(pr_number, merge_sha)

    if revert_pr:
        if rollback_id and state:
            state.update_rollback_status(rollback_id, "reverted", revert_pr=revert_pr)

        await do_notify_human(
            {
                "message": (
                    f"[ROLLBACK] PR #{pr_number} 머지 후 Sentry 에러 급증 ({delta}건)\n\n"
                    f"원인: 머지 5분 내 에러 +{delta}건 (임계값: {ROLLBACK_ERROR_THRESHOLD})\n"
                    f"조치: [사람] revert PR #{revert_pr} 확인 후 머지 필요"
                ),
                "level": "critical",
                "links": [
                    {
                        "text": f"원본 PR #{pr_number}",
                        "url": f"https://github.com/{REPO_FULL_NAME}/pull/{pr_number}",
                    },
                    {
                        "text": f"Revert PR #{revert_pr}",
                        "url": f"https://github.com/{REPO_FULL_NAME}/pull/{revert_pr}",
                    },
                ],
            }
        )
    else:
        if rollback_id and state:
            state.update_rollback_status(rollback_id, "revert_failed")

        await do_notify_human(
            {
                "message": (
                    f"[ROLLBACK] PR #{pr_number} revert PR 생성 실패\n\n"
                    f"원인: git revert 또는 PR 생성 중 오류\n"
                    f"조치: [사람] 수동 revert 필요"
                ),
                "level": "critical",
                "links": [
                    {
                        "text": f"원본 PR #{pr_number}",
                        "url": f"https://github.com/{REPO_FULL_NAME}/pull/{pr_number}",
                    },
                ],
            }
        )


async def _create_revert_pr(pr_number: int, merge_sha: str) -> int | None:
    """Create a revert PR via git clone in a temp directory."""
    # Get original PR title
    pr_title = await _get_pr_title(pr_number)
    revert_title = f'Revert "#{pr_number}: {pr_title}"' if pr_title else f"Revert PR #{pr_number}"
    branch_name = f"revert/PR-{pr_number}"

    with tempfile.TemporaryDirectory() as tmpdir:
        # Clone (full history — merge_sha may not be in shallow clone)
        ok = await _run_cmd(
            ["git", "clone", "--branch", "main", REPO_SSH_URL, tmpdir],
            timeout=GIT_CLONE_TIMEOUT,
        )
        if not ok:
            logger.error("git clone failed for revert PR #%d", pr_number)
            return None

        # Ensure label exists (after clone so gh has repo context)
        await _ensure_label(tmpdir)

        # Create revert branch
        ok = await _run_cmd(["git", "checkout", "-b", branch_name], cwd=tmpdir)
        if not ok:
            return None

        # Set git identity for revert commit
        ok = await _run_cmd(["git", "config", "user.name", GIT_BOT_NAME], cwd=tmpdir)
        if not ok:
            return None
        ok = await _run_cmd(
            ["git", "config", "user.email", GIT_BOT_EMAIL],
            cwd=tmpdir,
        )
        if not ok:
            return None

        # Revert the merge commit
        ok = await _run_cmd(["git", "revert", "--no-edit", "-m", "1", merge_sha], cwd=tmpdir)
        if not ok:
            logger.error(
                "git revert failed for PR #%d (sha=%s) — possible merge conflict",
                pr_number,
                merge_sha,
            )
            return None

        # Push
        ok = await _run_cmd(
            ["git", "push", "origin", branch_name], cwd=tmpdir, timeout=GIT_CLONE_TIMEOUT
        )
        if not ok:
            return None

        # Create PR
        revert_body = (
            f"## Auto-Rollback\n\n"
            f"Sentry 에러 급증 감지로 자동 생성된 revert PR입니다.\n\n"
            f"- 원본 PR: #{pr_number}\n"
            f"- Merge SHA: `{merge_sha}`\n"
            f"- 임계값: {ROLLBACK_ERROR_THRESHOLD}건"
        )
        from sdd_orchestrator.tools.github import _repo_args

        result = await _run_cmd_output(
            [
                "gh",
                "pr",
                "create",
                "--title",
                revert_title,
                "--body",
                revert_body,
                "--label",
                "auto-rollback",
                "--assignee",
                GH_ISSUE_ASSIGNEE,
                "--head",
                branch_name,
                "--base",
                "main",
                *_repo_args(),
            ],
            cwd=tmpdir,
            timeout=GH_PR_CREATE_TIMEOUT,
        )
        if not result:
            return None

        # Parse PR number from URL
        match = re.search(r"/pull/(\d+)", result)
        return int(match.group(1)) if match else None


async def _get_pr_title(pr_number: int) -> str:
    """Fetch PR title via gh CLI."""
    from sdd_orchestrator.tools.github import _repo_args

    result = await _run_cmd_output(
        ["gh", "pr", "view", str(pr_number), "--json", "title", "--jq", ".title",
         *_repo_args()],
        timeout=GH_TIMEOUT,
    )
    return result.strip() if result else ""


async def _ensure_label(cwd: str) -> None:
    """Ensure auto-rollback label exists (idempotent)."""
    from sdd_orchestrator.tools.github import _repo_args

    await _run_cmd(
        ["gh", "label", "create", "auto-rollback", "--color", "FF0000", "--force",
         *_repo_args()],
        cwd=cwd,
        timeout=GH_TIMEOUT,
    )


async def _run_cmd(cmd: list[str], *, cwd: str | None = None, timeout: int = GH_TIMEOUT) -> bool:
    """Run a subprocess command, return True on success."""
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode != 0:
            logger.warning("Command failed %s: %s", cmd[:3], stderr.decode().strip()[:200])
            return False
        return True
    except TimeoutError:
        logger.warning("Command timed out %s (%ds)", cmd[:3], timeout)
        if proc:
            proc.kill()
            await proc.communicate()
        return False
    except FileNotFoundError as e:
        logger.warning("Command error %s: %s", cmd[:3], e)
        return False


async def _run_cmd_output(
    cmd: list[str], *, cwd: str | None = None, timeout: int = GH_TIMEOUT
) -> str | None:
    """Run a subprocess command, return stdout on success."""
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode != 0:
            logger.warning("Command failed %s: %s", cmd[:3], stderr.decode().strip()[:200])
            return None
        return stdout.decode().strip()
    except TimeoutError:
        logger.warning("Command timed out %s (%ds)", cmd[:3], timeout)
        if proc:
            proc.kill()
            await proc.communicate()
        return None
    except FileNotFoundError as e:
        logger.warning("Command error %s: %s", cmd[:3], e)
        return None


def _get_state_store():
    """Get the shared StateStore instance (set by worktree module)."""
    from sdd_orchestrator.tools.worktree import _state_store

    return _state_store
