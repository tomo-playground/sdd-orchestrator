"""Shared helpers for SDD task management — status parsing, git ops, slug generation."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime
from pathlib import Path

from sdd_orchestrator.config import BACKLOG_PATH, TASKS_CURRENT_DIR, TASKS_DONE_DIR

logger = logging.getLogger(__name__)

# ── Status parsing ────────────────────────────────────────
# Matches frontmatter, blockquote, and markdown list variants:
#   status: approved | > status: approved | - **status**: approved | - status: approved
_STATUS_RE = re.compile(r"^(?:[-*]\s+)?(?:>\s*)?(?:\*\*)?status(?:\*\*)?:\s*(\w+)", re.MULTILINE)


def parse_spec_status(content: str) -> str:
    """Parse status from spec.md content (supports frontmatter and blockquote)."""
    match = _STATUS_RE.search(content)
    return match.group(1) if match else "pending"


def update_spec_status(content: str, new_status: str, metadata: str = "") -> str:
    """Replace status line in spec.md content. Handles frontmatter and blockquote."""
    status_line = f"> status: {new_status}"
    if metadata:
        status_line += f" | {metadata}"
    if _STATUS_RE.search(content):
        return _STATUS_RE.sub(status_line, content, count=1)
    # Insert after first heading if status line doesn't exist
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("# "):
            lines.insert(i + 1, f"\n{status_line}")
            break
    return "\n".join(lines)


# ── Git operations ────────────────────────────────────────
git_lock = asyncio.Lock()
GIT_CMD_TIMEOUT = 30  # seconds per git command


async def _wait_proc(proc, *, timeout: int = GIT_CMD_TIMEOUT) -> tuple[bytes, bytes]:
    """Wait for subprocess with bounded timeout; kills it on expiry."""
    try:
        return await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        proc.kill()
        await proc.wait()
        raise


async def git_commit_files(files: list[str], message: str) -> str | None:
    """Lock-protected git add + commit + push. Returns error message or None on success.

    Always runs in PROJECT_ROOT to avoid committing to the wrong repo
    when the process cwd is a different git repository.
    """
    from sdd_orchestrator.config import PROJECT_ROOT

    cwd = str(PROJECT_ROOT)

    async with git_lock:
        try:
            # git add
            proc = await asyncio.create_subprocess_exec(
                "git",
                "add",
                *files,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await _wait_proc(proc)
            if proc.returncode != 0:
                err = stderr.decode().strip()
                logger.warning("git add failed: %s", err)
                return f"git add failed: {err}"

            # git commit
            proc = await asyncio.create_subprocess_exec(
                "git",
                "commit",
                "-m",
                message,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await _wait_proc(proc)
            if proc.returncode != 0:
                err = stderr.decode().strip()
                logger.warning("git commit failed: %s", err)
                return f"git commit failed: {err}"

            # git push (with rebase retry)
            proc = await asyncio.create_subprocess_exec(
                "git",
                "push",
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await _wait_proc(proc)
            if proc.returncode != 0:
                logger.warning("git push failed, retrying with rebase")
                rebase = await asyncio.create_subprocess_exec(
                    "git",
                    "pull",
                    "--rebase",
                    cwd=cwd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, rebase_err = await _wait_proc(rebase)
                if rebase.returncode != 0:
                    err = rebase_err.decode().strip()
                    logger.error("git pull --rebase failed: %s", err)
                    return f"git pull --rebase failed: {err}"
                push2 = await asyncio.create_subprocess_exec(
                    "git",
                    "push",
                    cwd=cwd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, stderr2 = await _wait_proc(push2)
                if push2.returncode != 0:
                    err = stderr2.decode().strip()
                    logger.error("git push retry failed: %s", err)
                    return f"git push retry failed: {err}"

            return None
        except TimeoutError:
            logger.error("git command timed out after %ss", GIT_CMD_TIMEOUT)
            return f"git command timed out after {GIT_CMD_TIMEOUT}s"
        except Exception as e:
            logger.exception("git commit/push error")
            return f"git error: {e}"


# ── SP number / slug ─────────────────────────────────────
_SP_NUM_RE = re.compile(r"SP-(\d+)")


def next_sp_number(
    current_dir: Path = TASKS_CURRENT_DIR,
    done_dir: Path = TASKS_DONE_DIR,
    backlog_path: Path = BACKLOG_PATH,
) -> int:
    """Scan current/ + done/ + backlog.md for max SP number, return max+1."""
    max_num = 0

    for d in (current_dir, done_dir):
        if not d.exists():
            continue
        for child in d.iterdir():
            m = _SP_NUM_RE.search(child.name)
            if m:
                max_num = max(max_num, int(m.group(1)))

    if backlog_path.exists():
        text = backlog_path.read_text(encoding="utf-8")
        for m in _SP_NUM_RE.finditer(text):
            max_num = max(max_num, int(m.group(1)))

    return max_num + 1


def generate_slug(title: str, max_len: int = 40) -> str:
    """Generate filesystem-safe slug from title. Handles Korean-only titles."""
    slug = title.lower()
    # Keep only alphanumeric and hyphens (remove Korean, special chars)
    slug = re.sub(r"[^a-z0-9\-]", "-", slug)
    # Collapse consecutive hyphens
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        slug = "task"
    return slug[:max_len]


# ── MCP response helpers ─────────────────────────────────
def _ok(message: str) -> dict:
    return {"content": [{"type": "text", "text": message}]}


def _error(message: str) -> dict:
    return {"content": [{"type": "text", "text": f"Error: {message}"}], "isError": True}


# ── Date helper ───────────────────────────────────────────
def today_str() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")
