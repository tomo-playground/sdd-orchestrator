"""sdd init — initialize SDD structure in the current project."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# Files to create from templates (relative to project root)
_INIT_FILES = [
    ("sdd.config.yaml", "sdd.config.yaml"),
    (".claude/tasks/backlog.md", "backlog.md"),
    (".github/workflows/sdd-sync.yml", "workflows/sdd-sync.yml"),
    (".github/workflows/health-check.yml", "workflows/health-check.yml"),
]

# Directories to create
_INIT_DIRS = [
    ".claude/tasks/current",
    ".claude/tasks/done",
    ".claude/agents",
    ".claude/skills",
]


def run_init(*, preset: str = "default", force: bool = False) -> int:
    """Initialize SDD project structure.

    Creates sdd.config.yaml, task directories, and workflow templates.
    Returns 0 on success, 1 on error.
    """
    project_root = Path.cwd()
    created = 0
    skipped = 0
    errors = 0

    # Create directories
    for dir_path in _INIT_DIRS:
        full = project_root / dir_path
        full.mkdir(parents=True, exist_ok=True)

    # Copy template files
    for dest_rel, template_name in _INIT_FILES:
        dest = project_root / dest_rel
        src = _TEMPLATES_DIR / template_name

        if not src.exists():
            logger.warning("Template not found: %s", src)
            errors += 1
            continue

        if dest.exists() and not force:
            logger.info("Skipped (exists): %s", dest_rel)
            skipped += 1
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src, dest)
            logger.info("Created: %s", dest_rel)
            created += 1
        except OSError:
            logger.exception("Failed to copy template: %s -> %s", src, dest)
            errors += 1

    print(f"SDD initialized: {created} files created, {skipped} skipped.")
    if errors:
        print(f"Errors: {errors} — check logs for details.")
    if skipped:
        print("Use --force to overwrite existing files.")
    return 1 if errors else 0
