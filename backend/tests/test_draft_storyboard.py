"""Tests for draft storyboard creation (POST /storyboards/draft).

Covers both API integration tests (TestClient) and service-layer unit tests.
Uses SQLite in-memory DB via conftest.py fixtures (db_session, client).
"""

from __future__ import annotations

from unittest.mock import patch

from tests.conftest import SVC

# ===========================================================================
# 1. API Integration Tests
# ===========================================================================


class TestDraftStoryboardAPI:
    """Integration tests for POST /storyboards/draft endpoint."""

    def test_create_draft_returns_id(self, client):
        """Draft 생성 시 storyboard_id, title, created=True를 반환한다."""
        resp = client.post(
            f"{SVC}/storyboards/draft",
            json={"title": "My Draft", "group_id": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["storyboard_id"] > 0
        assert data["title"] == "My Draft"
        assert data["created"] is True

    def test_draft_with_default_title(self, client):
        """title 미지정 시 기본값 'Draft'를 사용한다."""
        resp = client.post(
            f"{SVC}/storyboards/draft",
            json={"group_id": 1},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Draft"

    def test_draft_is_retrievable(self, client):
        """생성된 draft를 GET /storyboards/{id}로 조회할 수 있다."""
        create_resp = client.post(
            f"{SVC}/storyboards/draft",
            json={"title": "Retrievable Draft", "group_id": 1},
        )
        sb_id = create_resp.json()["storyboard_id"]

        get_resp = client.get(f"{SVC}/storyboards/{sb_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["title"] == "Retrievable Draft"
        assert get_resp.json()["scenes"] == []

    def test_draft_missing_group_id(self, client):
        """group_id 누락 시 422 Validation Error를 반환한다."""
        resp = client.post(
            f"{SVC}/storyboards/draft",
            json={"title": "No Group"},
        )
        assert resp.status_code == 422


# ===========================================================================
# 2. Service Layer Unit Tests
# ===========================================================================


class TestCreateDraft:
    """Unit tests for create_draft() service function."""

    def test_returns_storyboard_id_title_created(self, db_session):
        """create_draft()가 storyboard_id, title, created=True를 반환한다."""
        from services.storyboard.crud import create_draft

        result = create_draft(db_session, "My First Draft", 1)

        assert result["storyboard_id"] > 0
        assert result["title"] == "My First Draft"
        assert result["created"] is True

    def test_default_title_when_empty(self, db_session):
        """빈 title 전달 시 'Draft' 기본값이 적용된다."""
        from services.storyboard.crud import create_draft

        result = create_draft(db_session, "", 1)

        assert result["title"] == "Draft"

    def test_default_title_when_none(self, db_session):
        """None title 전달 시 'Draft' 기본값이 적용된다."""
        from services.storyboard.crud import create_draft

        result = create_draft(db_session, None, 1)

        assert result["title"] == "Draft"

    @patch("services.characters.resolve_speaker_to_character", return_value=None)
    @patch("services.config_resolver.resolve_effective_config", return_value={"values": {}})
    def test_draft_retrievable_by_get_storyboard(self, mock_config, mock_speaker, db_session):
        """생성된 draft가 get_storyboard_by_id()로 조회 가능하다."""
        from services.storyboard.crud import create_draft, get_storyboard_by_id

        result = create_draft(db_session, "Lookup Draft", 1)
        sb_id = result["storyboard_id"]

        detail = get_storyboard_by_id(db_session, sb_id)

        assert detail["id"] == sb_id
        assert detail["title"] == "Lookup Draft"

    def test_draft_scenes_empty(self, db_session):
        """생성된 draft의 scenes가 빈 리스트이다."""
        from models.storyboard import Storyboard
        from services.storyboard.crud import create_draft

        result = create_draft(db_session, "Empty Draft", 1)
        sb = db_session.get(Storyboard, result["storyboard_id"])

        assert sb is not None
        assert len(sb.scenes) == 0

    def test_draft_group_id_persisted(self, db_session):
        """전달한 group_id가 DB에 정확히 저장된다."""
        from models.storyboard import Storyboard
        from services.storyboard.crud import create_draft

        result = create_draft(db_session, "Group Test", 1)
        sb = db_session.get(Storyboard, result["storyboard_id"])

        assert sb.group_id == 1

    def test_draft_version_is_one(self, db_session):
        """신규 draft의 version은 1이다."""
        from models.storyboard import Storyboard
        from services.storyboard.crud import create_draft

        result = create_draft(db_session, "Version Check", 1)
        sb = db_session.get(Storyboard, result["storyboard_id"])

        assert sb.version == 1
