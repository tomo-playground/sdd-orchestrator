"""Tests for path traversal prevention utilities."""

import pytest
from fastapi import HTTPException

from services.path_security import safe_resolve_path, safe_storage_path


class TestSafeResolvePath:
    """Tests for safe_resolve_path (router-facing, raises HTTPException)."""

    def test_normal_filename(self, tmp_path):
        result = safe_resolve_path(tmp_path, "font.ttf")
        assert result == (tmp_path / "font.ttf").resolve()

    def test_subdirectory(self, tmp_path):
        result = safe_resolve_path(tmp_path, "subdir/file.txt")
        assert result == (tmp_path / "subdir" / "file.txt").resolve()

    def test_parent_traversal_blocked(self, tmp_path):
        with pytest.raises(HTTPException) as exc_info:
            safe_resolve_path(tmp_path, "../../../etc/passwd")
        assert exc_info.value.status_code == 400

    def test_absolute_path_blocked(self, tmp_path):
        with pytest.raises(HTTPException) as exc_info:
            safe_resolve_path(tmp_path, "/etc/passwd")
        assert exc_info.value.status_code == 400

    def test_nested_traversal_blocked(self, tmp_path):
        with pytest.raises(HTTPException) as exc_info:
            safe_resolve_path(tmp_path, "foo/../../bar")
        # foo/../../bar resolves to ../bar which escapes tmp_path
        assert exc_info.value.status_code == 400

    def test_dot_dot_in_middle_still_inside(self, tmp_path):
        # subdir/../file.txt resolves to file.txt inside tmp_path
        result = safe_resolve_path(tmp_path, "subdir/../file.txt")
        assert result == (tmp_path / "file.txt").resolve()


class TestSafeStoragePath:
    """Tests for safe_storage_path (service-facing, raises ValueError)."""

    def test_normal_key(self, tmp_path):
        result = safe_storage_path(tmp_path, "projects/1/image.png")
        assert result == (tmp_path / "projects" / "1" / "image.png").resolve()

    def test_parent_traversal_blocked(self, tmp_path):
        with pytest.raises(ValueError, match="Path traversal blocked"):
            safe_storage_path(tmp_path, "../../etc/passwd")

    def test_absolute_path_blocked(self, tmp_path):
        with pytest.raises(ValueError, match="Path traversal blocked"):
            safe_storage_path(tmp_path, "/etc/passwd")

    def test_nested_traversal_blocked(self, tmp_path):
        with pytest.raises(ValueError, match="Path traversal blocked"):
            safe_storage_path(tmp_path, "a/b/../../../../etc/shadow")
