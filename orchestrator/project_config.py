"""Project-specific configuration loaded from sdd.config.yaml.

Engine-agnostic: the orchestrator engine reads project-specific values
(GitHub repo, Sentry projects, task paths, etc.) from this module instead
of hard-coding them in config.py.

Priority: env var > YAML > code default.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from string import Template

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_YAML_CANDIDATES = ["sdd.config.yaml", ".sdd/config.yaml"]
_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


@dataclass(frozen=True)
class ProjectConfig:
    """Project-specific settings injected via sdd.config.yaml."""

    gh_repo_owner: str = "tomo-playground"
    gh_repo_name: str = "shorts-producer"
    gh_issue_assignee: str = "stopper2008"
    sentry_org: str = "tomo-playground"
    sentry_projects: tuple[str, ...] = (
        "shorts-producer-backend",
        "shorts-producer-frontend",
        "shorts-producer-audio",
    )
    tasks_dir: str = ".claude/tasks"
    backlog_file: str = "backlog.md"

    @property
    def gh_repo_url(self) -> str:
        return f"https://github.com/{self.gh_repo_owner}/{self.gh_repo_name}"

    @property
    def repo_full_name(self) -> str:
        return f"{self.gh_repo_owner}/{self.gh_repo_name}"

    @property
    def repo_ssh_url(self) -> str:
        return f"git@github.com:{self.gh_repo_owner}/{self.gh_repo_name}.git"

    @property
    def backlog_path(self) -> Path:
        return _PROJECT_ROOT / self.tasks_dir / self.backlog_file

    @property
    def tasks_current_dir(self) -> Path:
        return _PROJECT_ROOT / self.tasks_dir / "current"

    @property
    def tasks_done_dir(self) -> Path:
        return _PROJECT_ROOT / self.tasks_dir / "done"


def _as_dict(value: object) -> dict:
    """Return value if it is a dict, otherwise an empty dict."""
    return value if isinstance(value, dict) else {}


def _load_yaml_file() -> dict:
    """Load the first found sdd.config.yaml. Returns {} on failure."""
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        logger.debug("PyYAML not installed — using default config")
        return {}

    for candidate in _YAML_CANDIDATES:
        path = _PROJECT_ROOT / candidate
        if path.is_file():
            try:
                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                if not isinstance(data, dict):
                    logger.warning(
                        "Ignoring %s: top-level YAML is not a mapping (got %s)",
                        path,
                        type(data).__name__,
                    )
                    return {}
                logger.debug("Loaded project config from %s", path)
                return data
            except Exception:
                logger.warning("Failed to parse %s — falling back to defaults", path, exc_info=True)
                return {}
    return {}


def _env_or(yaml_val: str | None, env_key: str, default: str) -> str:
    """env > YAML > default."""
    env = os.environ.get(env_key)
    if env is not None:
        return env
    if yaml_val is not None:
        return str(yaml_val)
    return default


def _build_config(data: dict) -> ProjectConfig:
    """Build ProjectConfig from parsed YAML dict."""
    project = _as_dict(data.get("project"))
    gh = _as_dict(project.get("github"))
    sentry = _as_dict(project.get("sentry"))
    tasks = _as_dict(project.get("tasks"))

    sentry_projects_yaml = sentry.get("projects")
    sentry_projects: tuple[str, ...]
    # sentry_projects: 리스트 타입이므로 env override 미지원 (YAML 또는 default만)
    if sentry_projects_yaml and isinstance(sentry_projects_yaml, list):
        sentry_projects = tuple(sentry_projects_yaml)
    else:
        sentry_projects = ProjectConfig.sentry_projects

    return ProjectConfig(
        gh_repo_owner=_env_or(gh.get("owner"), "SDD_GH_OWNER", ProjectConfig.gh_repo_owner),
        gh_repo_name=_env_or(gh.get("repo"), "SDD_GH_REPO", ProjectConfig.gh_repo_name),
        gh_issue_assignee=_env_or(
            gh.get("assignee"), "SDD_GH_ASSIGNEE", ProjectConfig.gh_issue_assignee
        ),
        sentry_org=_env_or(sentry.get("org"), "SDD_SENTRY_ORG", ProjectConfig.sentry_org),
        sentry_projects=sentry_projects,
        tasks_dir=_env_or(tasks.get("dir"), "SDD_TASKS_DIR", ProjectConfig.tasks_dir),
        backlog_file=_env_or(tasks.get("backlog"), "SDD_BACKLOG_FILE", ProjectConfig.backlog_file),
    )


@lru_cache(maxsize=1)
def get_project_config() -> ProjectConfig:
    """Load and cache the project config. Thread-safe via lru_cache."""
    data = _load_yaml_file()
    return _build_config(data)


def load_prompt(name: str) -> str:
    """Load a prompt from orchestrator/prompts/{name}.md.

    Template variables like ``${gh_repo_owner}`` are substituted from
    the current ``ProjectConfig``. Missing .md files fall back to an
    empty string (callers should provide their own fallback).
    """
    path = _PROMPTS_DIR / f"{name}.md"
    if not path.is_file():
        logger.warning("Prompt file not found: %s — using empty string", path)
        return ""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        logger.warning("Failed to read prompt file %s", path, exc_info=True)
        return ""

    cfg = get_project_config()
    substitutions = {
        "gh_repo_owner": cfg.gh_repo_owner,
        "gh_repo_name": cfg.gh_repo_name,
        "gh_issue_assignee": cfg.gh_issue_assignee,
        "sentry_org": cfg.sentry_org,
        "repo_full_name": cfg.repo_full_name,
    }
    return Template(raw).safe_substitute(substitutions)
