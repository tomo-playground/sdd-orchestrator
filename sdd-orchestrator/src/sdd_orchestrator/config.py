"""Orchestrator configuration constants.

Project-specific values (GitHub repo, Sentry projects, task paths, prompts)
are managed by ``project_config.py`` and ``sdd.config.yaml``.
This module retains engine-level defaults and a ``__getattr__`` compatibility
layer so that existing ``from sdd_orchestrator.config import X`` continues to work.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from package dir (fallback), then project root
load_dotenv(Path(__file__).resolve().parent / ".env")

# ── Paths ──────────────────────────────────────────────────
PROJECT_ROOT = Path(os.environ.get("SDD_PROJECT_ROOT", Path.cwd()))
DEFAULT_DB_PATH = PROJECT_ROOT / ".sdd" / "state.db"

# ── Daemon ─────────────────────────────────────────────────
CYCLE_INTERVAL = 180  # 3 minutes in seconds
MAX_AGENT_TURNS = 15
AGENT_QUERY_TIMEOUT = 600  # seconds — query_agent asyncio timeout

# ── Feature Flags ──────────────────────────────────────────
ENABLE_AUTO_DESIGN = os.environ.get("ORCH_AUTO_DESIGN", "0") == "1"

# ── Auto-Run (Phase 2) ────────────────────────────────────
MAX_PARALLEL_RUNS = int(os.environ.get("ORCH_MAX_PARALLEL", "2"))
ENABLE_AUTO_RUN = os.environ.get("ORCH_AUTO_RUN", "0") == "1"

# ── Lead Agent ─────────────────────────────────────────────
LEAD_AGENT_MODEL = "claude-sonnet-4-6"

# ── Designer Agent ─────────────────────────────────────────
DESIGNER_MODEL = "claude-opus-4-6"
DESIGN_TIMEOUT = 600  # 10 minutes
MAX_AUTO_APPROVE_FILES = 6

# ── GitHub CLI ─────────────────────────────────────────────
GH_TIMEOUT = 15  # seconds
GH_PR_FIELDS = "number,title,headRefName,state,reviewDecision,statusCheckRollup,labels,url"
GH_RUN_FIELDS = "databaseId,workflowName,status,conclusion,headBranch,createdAt"
GH_RUN_LIMIT = 10
STUCK_THRESHOLD_MINUTES = 30

# ── Sentry (engine-level, non-project) ───────────────────
SENTRY_AUTH_TOKEN = os.environ.get("SENTRY_AUTH_TOKEN", "")
SENTRY_API_BASE = "https://sentry.io/api/0"
SENTRY_SCAN_INTERVAL = 3600  # 1 hour in seconds
SENTRY_SCAN_LOOKBACK_HOURS = 2
SENTRY_TIMEOUT_CONNECT = 5.0
SENTRY_TIMEOUT_READ = 15.0
SENTRY_TIMEOUT_WRITE = 5.0
SENTRY_TIMEOUT_POOL = 5.0

# ── Rollback ─────────────────────────────────────────
ROLLBACK_ERROR_THRESHOLD = int(os.environ.get("ORCH_ROLLBACK_THRESHOLD", "5"))
ROLLBACK_MONITOR_DURATION = 300  # 5 minutes
ROLLBACK_CHECK_INTERVAL = 30  # 30 seconds
ROLLBACK_LOOKBACK_HOURS = 0.1  # 6 minutes lookback window
ROLLBACK_MAX_FETCH_FAILURES = 3
SENTRY_LOOKBACK_ALL_HOURS = (
    720  # 30 days — broad window so lastSeen filter (not firstSeen) drives inclusion
)
GIT_CLONE_TIMEOUT = 60
GH_PR_CREATE_TIMEOUT = 30
GIT_BOT_NAME = "orchestrator[bot]"
GIT_BOT_EMAIL = "orchestrator[bot]@users.noreply.github.com"

# ── Slack ─────────────────────────────────────────────────
SLACK_TIMEOUT_CONNECT = 5.0
SLACK_TIMEOUT_READ = 10.0
SLACK_MIN_INTERVAL = 1.0  # seconds — rate limit guard (1 msg/sec)
SLACK_MAX_MESSAGE_LENGTH = 4000
SLACK_BLOCK_TEXT_MAX = 3000  # Slack section block text field limit
SLACK_BLOCK_BUDGET = 2900  # per-message total char budget for agent responses
SLACK_BUTTON_TEXT_MAX = 75  # Slack button label character limit

# ── Slack Bot (Socket Mode) ──────────────────────────────
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")  # xapp- prefix, Socket Mode
SLACK_BOT_API_TIMEOUT = 10.0  # chat_postMessage timeout
SLACK_BOT_CHAT_INTERVAL = 0.5  # rate limit guard (500ms)
SLACK_BOT_ALLOWED_CHANNEL = os.environ.get(
    "SLACK_BOT_ALLOWED_CHANNEL", ""
)  # single channel ID, empty = all
SLACK_BOT_ALLOWED_USERS = os.environ.get(
    "SLACK_BOT_ALLOWED_USERS", ""
)  # comma-separated Slack user IDs, empty = all

# ── Slack Bot Agent ──────────────────────────────────────
SLACK_BOT_AGENT_MODEL = os.environ.get("SLACK_BOT_AGENT_MODEL", "claude-sonnet-4-6")
SLACK_BOT_MAX_TURNS = 12
SLACK_BOT_AGENT_TIMEOUT = 120  # seconds — Sonnet is slower than Haiku

# ── GitHub Actions Control ────────────────────────────────
GH_MONITORED_WORKFLOWS = [
    "sdd-review.yml",
    "sdd-fix.yml",
    "sdd-sync.yml",
    "sentry-autofix.yml",
]

# ── Compatibility Layer ──────────────────────────────────
# Existing code uses ``from sdd_orchestrator.config import GH_REPO_OWNER`` etc.
# This __getattr__ transparently delegates to ProjectConfig.

_PROJECT_ATTR_MAP: dict[str, str] = {
    "GH_REPO_OWNER": "gh_repo_owner",
    "GH_REPO_NAME": "gh_repo_name",
    "GH_REPO_URL": "gh_repo_url",
    "GH_ISSUE_ASSIGNEE": "gh_issue_assignee",
    "SENTRY_ORG": "sentry_org",
    "SENTRY_PROJECTS": "sentry_projects",
    "BACKLOG_PATH": "backlog_path",
    "TASKS_CURRENT_DIR": "tasks_current_dir",
    "TASKS_DONE_DIR": "tasks_done_dir",
    "REPO_SSH_URL": "repo_ssh_url",
    "REPO_FULL_NAME": "repo_full_name",
}

_PROMPT_NAMES: dict[str, str] = {
    "LEAD_AGENT_SYSTEM_PROMPT": "lead_agent",
    "DESIGNER_SYSTEM_PROMPT": "designer",
    "SLACK_BOT_AGENT_PROMPT": "slack_bot",
}


def _apply_engine_overrides() -> None:
    """Apply YAML engine overrides to module-level constants."""
    import yaml  # noqa: PLC0415

    yaml_path = None
    for candidate in ("sdd.config.yaml", ".sdd/config.yaml"):
        candidate_path = PROJECT_ROOT / candidate
        if candidate_path.is_file():
            yaml_path = candidate_path
            break
    if yaml_path is None:
        return
    try:
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:  # noqa: BLE001
        return
    engine = data.get("engine", {})
    if not engine:
        return
    g = globals()
    if "cycle_interval" in engine:
        g["CYCLE_INTERVAL"] = int(engine["cycle_interval"])
    if "max_parallel_runs" in engine:
        g["MAX_PARALLEL_RUNS"] = int(engine["max_parallel_runs"])


try:
    _apply_engine_overrides()
except Exception:
    pass  # YAML/PyYAML unavailable — keep defaults


def __getattr__(name: str):
    """Compatibility layer: delegate project-specific attrs to ProjectConfig."""
    if name in _PROJECT_ATTR_MAP:
        from sdd_orchestrator.project_config import get_project_config  # noqa: PLC0415

        cfg = get_project_config()
        val = getattr(cfg, _PROJECT_ATTR_MAP[name])
        # SENTRY_PROJECTS: ProjectConfig stores tuple, consumers expect list
        if name == "SENTRY_PROJECTS":
            return list(val)
        return val

    if name in _PROMPT_NAMES:
        from sdd_orchestrator.project_config import load_prompt  # noqa: PLC0415

        prompt = load_prompt(_PROMPT_NAMES[name])
        if not prompt:
            raise RuntimeError(
                f"Required prompt file is missing or empty: "
                f"sdd_orchestrator/prompts/{_PROMPT_NAMES[name]}.md"
            )
        return prompt

    raise AttributeError(f"module 'sdd_orchestrator.config' has no attribute {name!r}")
