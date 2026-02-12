"""Path traversal prevention utilities."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException


def safe_resolve_path(base_dir: Path, user_input: str) -> Path:
    """Resolve and validate path stays within base_dir (router-facing).

    Raises HTTPException(400) on traversal attempt.
    """
    resolved = (base_dir / user_input).resolve()
    if not resolved.is_relative_to(base_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid file path.")
    return resolved


def safe_storage_path(base_dir: Path, key: str) -> Path:
    """Resolve and validate path stays within base_dir (service-facing).

    Raises ValueError on traversal attempt.
    """
    resolved = (base_dir / key).resolve()
    if not resolved.is_relative_to(base_dir.resolve()):
        raise ValueError(f"Path traversal blocked: {key}")
    return resolved
