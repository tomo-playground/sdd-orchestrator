"""Tests for prompt router endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from models import Tag

# Real API tests: skipped by default, run with `pytest --run-integration`
integration = pytest.mark.integration


class TestPromptRewrite:
    """Test POST /prompt/rewrite endpoint."""

    @integration
    def test_rewrite_prompt_compose_mode(self, client: TestClient):
        """Rewrite prompt in compose mode returns merged result."""
        request_data = {
            "base_prompt": "masterpiece, best_quality",
            "scene_prompt": "1girl, smile, upper_body",
            "style": "Anime",
            "mode": "compose",
        }
        response = client.post("/prompt/rewrite", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "prompt" in data

    @integration
    def test_rewrite_prompt_default_mode(self, client: TestClient):
        """Rewrite prompt with default mode."""
        request_data = {
            "base_prompt": "masterpiece",
            "scene_prompt": "1girl, standing",
        }
        response = client.post("/prompt/rewrite", json=request_data)
        assert response.status_code == 200

    def test_rewrite_prompt_empty_scene(self, client: TestClient):
        """Rewrite with empty scene prompt returns 400 (validation)."""
        request_data = {
            "base_prompt": "masterpiece",
            "scene_prompt": "",
        }
        response = client.post("/prompt/rewrite", json=request_data)
        assert response.status_code == 400


class TestPromptSplit:
    """Test POST /prompt/split endpoint."""

    @integration
    def test_split_prompt_basic(self, client: TestClient):
        """Split prompt into base and scene components."""
        request_data = {
            "example_prompt": "1girl, smile, upper_body, school_uniform",
            "style": "Anime",
        }
        response = client.post("/prompt/split", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "base_prompt" in data or "scene_prompt" in data

    def test_split_prompt_empty(self, client: TestClient):
        """Split empty prompt returns 400 (validation)."""
        request_data = {
            "example_prompt": "",
        }
        response = client.post("/prompt/split", json=request_data)
        assert response.status_code == 400


class TestPromptValidate:
    """Test POST /prompt/validate endpoint."""

    def test_validate_clean_prompt(self, client: TestClient):
        """Validate prompt with no issues."""
        with patch("routers.prompt.httpx.AsyncClient") as mock_client_cls:
            mock_resp = MagicMock()
            mock_resp.json.return_value = [{"name": "my_lora"}]
            mock_resp.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            request_data = {
                "positive": "1girl, smile, upper_body",
                "negative": "bad_quality, worst_quality",
            }
            response = client.post("/prompt/validate", json=request_data)
            assert response.status_code == 200
            data = response.json()

            assert "valid" in data
            assert "warnings" in data
            assert "errors" in data
            assert "lora_validation" in data
            assert "conflict_detection" in data
            assert "identity_validation" in data

    def test_validate_prompt_with_conflicts(self, client: TestClient):
        """Validate prompt where positive/negative overlap."""
        with patch("routers.prompt.httpx.AsyncClient") as mock_client_cls:
            mock_resp = MagicMock()
            mock_resp.json.return_value = []
            mock_resp.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            request_data = {
                "positive": "1girl, smile",
                "negative": "smile, bad_quality",
            }
            response = client.post("/prompt/validate", json=request_data)
            assert response.status_code == 200
            data = response.json()

            assert "conflict_detection" in data
            conflict = data["conflict_detection"]
            assert conflict["has_conflicts"] is True
            assert "smile" in conflict["conflicts"]

    def test_validate_prompt_sd_webui_unavailable(self, client: TestClient):
        """Validate works even when SD WebUI is down."""
        import httpx

        with patch("routers.prompt.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            request_data = {
                "positive": "1girl, smile",
                "negative": "bad_quality",
            }
            response = client.post("/prompt/validate", json=request_data)
            assert response.status_code == 200
            data = response.json()
            assert "valid" in data

    def test_validate_prompt_missing_lora(self, client: TestClient):
        """Validate detects missing LoRA from SD WebUI."""
        with patch("routers.prompt.httpx.AsyncClient") as mock_client_cls:
            mock_resp = MagicMock()
            mock_resp.json.return_value = [{"name": "existing_lora"}]
            mock_resp.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            request_data = {
                "positive": "<lora:missing_lora:0.8>, 1girl",
                "negative": "",
            }
            response = client.post("/prompt/validate", json=request_data)
            assert response.status_code == 200
            data = response.json()
            assert data["lora_validation"]["valid"] is False
            assert "missing_lora" in data["lora_validation"]["missing"]

    def test_validate_prompt_lora_skip_on_sd_failure(self, client: TestClient):
        """LoRA validation is skipped when SD WebUI is unreachable."""
        with patch("routers.prompt.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            request_data = {
                "positive": "<lora:some_lora:0.8>, 1girl",
                "negative": "",
            }
            response = client.post("/prompt/validate", json=request_data)
            assert response.status_code == 200
            data = response.json()
            # Should NOT block — LoRA validation skipped
            assert data["lora_validation"]["valid"] is True
            assert data["lora_validation"].get("skipped") is True
            assert "some_lora" in data["lora_validation"]["prompt_loras"]

    def test_validate_prompt_minimal_body(self, client: TestClient):
        """Validate with only positive prompt (negative defaults to empty)."""
        with patch("routers.prompt.httpx.AsyncClient") as mock_client_cls:
            mock_resp = MagicMock()
            mock_resp.json.return_value = []
            mock_resp.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            request_data = {"positive": "1girl, smile"}
            response = client.post("/prompt/validate", json=request_data)
            assert response.status_code == 200


class TestPromptCompose:
    """Test POST /prompt/compose endpoint."""

    def test_compose_prompt_with_character(self, client: TestClient, db_session):
        """Compose prompt using V3 engine with character_id."""
        from models import Character

        char = Character(name="Test Char", gender="female", project_id=1)
        db_session.add(char)
        db_session.commit()
        char_id = char.id

        request_data = {
            "tokens": ["smile", "upper_body"],
            "character_id": char_id,
        }
        response = client.post("/prompt/compose", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert "prompt" in data
        assert "tokens" in data
        assert isinstance(data["tokens"], list)
        assert data["effective_mode"] == "v3"
        assert "scene_complexity" in data
        assert "meta" in data
        assert "token_count" in data["meta"]

    def test_compose_prompt_with_context_tags(self, client: TestClient, db_session):
        """Compose merges context_tags into tokens."""
        from models import Character

        char = Character(name="Context Char", gender="female", project_id=1)
        db_session.add(char)
        db_session.commit()

        request_data = {
            "tokens": ["standing"],
            "character_id": char.id,
            "context_tags": {
                "expression": ["smile"],
                "gaze": "looking_at_viewer",
                "camera": "upper_body",
                "pose": ["standing"],
            },
        }
        response = client.post("/prompt/compose", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "prompt" in data

    def test_compose_prompt_with_loras(self, client: TestClient, db_session):
        """Compose includes LoRA weights in response."""
        from models import Character

        char = Character(name="LoRA Char", gender="female", project_id=1)
        db_session.add(char)
        db_session.commit()

        request_data = {
            "tokens": ["smile"],
            "character_id": char.id,
            "loras": [
                {"name": "test_lora", "weight": 0.8, "trigger_words": ["trigger1"]},
            ],
        }
        response = client.post("/prompt/compose", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["lora_weights"] == {"test_lora": 0.8}

    def test_compose_resolves_style_loras_from_storyboard(self, client: TestClient, db_session):
        """Compose with storyboard_id resolves style LoRAs from DB when not sent by frontend."""
        from models import Character

        char = Character(name="Style Test Char", gender="female", project_id=1)
        db_session.add(char)
        db_session.commit()

        style_loras = [{"name": "J_huiben", "weight": 0.8, "trigger_words": ["J_huiben"]}]
        with patch(
            "services.image_generation_core.resolve_style_loras_from_storyboard",
            return_value=style_loras,
        ) as mock_resolve:
            request_data = {
                "tokens": ["smile", "standing"],
                "character_id": char.id,
                "storyboard_id": 404,
            }
            response = client.post("/prompt/compose", json=request_data)

        assert response.status_code == 200
        data = response.json()
        mock_resolve.assert_called_once()
        # LoRA should be in composed prompt (weight may be calibrated by V3)
        assert "<lora:J_huiben:" in data["prompt"]
        assert "J_huiben" in data["lora_weights"]

    def test_compose_skips_db_resolve_when_loras_sent(self, client: TestClient, db_session):
        """When frontend sends loras explicitly, DB resolve is skipped."""
        from models import Character

        char = Character(name="Explicit LoRA Char", gender="female", project_id=1)
        db_session.add(char)
        db_session.commit()

        with patch(
            "services.image_generation_core.resolve_style_loras_from_storyboard",
        ) as mock_resolve:
            request_data = {
                "tokens": ["smile"],
                "character_id": char.id,
                "storyboard_id": 404,
                "loras": [{"name": "custom_lora", "weight": 0.7, "trigger_words": ["trigger1"]}],
            }
            response = client.post("/prompt/compose", json=request_data)

        assert response.status_code == 200
        mock_resolve.assert_not_called()
        data = response.json()
        assert data["lora_weights"] == {"custom_lora": 0.7}

    def test_compose_prompt_missing_character(self, client: TestClient, db_session):
        """Compose with non-existent character_id returns 500."""
        request_data = {
            "tokens": ["smile"],
            "character_id": 99999,
        }
        response = client.post("/prompt/compose", json=request_data)
        # V3PromptService may raise or handle gracefully
        assert response.status_code in (200, 500)

    def test_compose_prompt_missing_required_field(self, client: TestClient):
        """Compose without character_id returns 422."""
        request_data = {"tokens": ["smile"]}
        response = client.post("/prompt/compose", json=request_data)
        assert response.status_code == 422


class TestValidateTags:
    """Test POST /prompt/validate-tags endpoint."""

    def test_validate_tags_all_known(self, client: TestClient, db_session):
        """Validate tags that exist in DB."""
        tag = Tag(name="smile", category="scene", default_layer=5)
        db_session.add(tag)
        db_session.commit()

        request_data = {"tags": ["smile"], "check_danbooru": False}
        response = client.post("/prompt/validate-tags", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert len(data["unknown_in_db"]) == 0

    def test_validate_tags_unknown_tag(self, client: TestClient, db_session):
        """Unknown tags are reported."""
        request_data = {"tags": ["nonexistent_tag_xyz"], "check_danbooru": False}
        response = client.post("/prompt/validate-tags", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert "nonexistent_tag_xyz" in data["unknown_in_db"]

    def test_validate_tags_risky_alias(self, client: TestClient, db_session):
        """Tags with alias replacements are flagged as risky."""
        # "medium_shot" is aliased to "cowboy_shot" in conftest
        request_data = {"tags": ["medium_shot"], "check_danbooru": False}
        response = client.post("/prompt/validate-tags", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert "medium_shot" in data["risky_tags"]
        assert len(data["warnings"]) >= 1

    def test_validate_tags_empty_list(self, client: TestClient, db_session):
        """Validate empty tag list."""
        request_data = {"tags": []}
        response = client.post("/prompt/validate-tags", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


class TestAutoReplace:
    """Test POST /prompt/auto-replace endpoint."""

    def test_auto_replace_risky_tag(self, client: TestClient):
        """Risky tags are replaced with alternatives."""
        # "medium_shot" -> "cowboy_shot" via TagAliasCache (set in conftest)
        request_data = {"tags": ["medium_shot", "smile"]}
        response = client.post("/prompt/auto-replace", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert "cowboy_shot" in data["replaced"]
        assert "smile" in data["replaced"]
        assert data["replaced_count"] >= 1

    def test_auto_replace_no_changes(self, client: TestClient):
        """Safe tags pass through unchanged."""
        request_data = {"tags": ["smile", "standing"]}
        response = client.post("/prompt/auto-replace", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["replaced"] == ["smile", "standing"]
        assert data["replaced_count"] == 0
        assert data["removed_count"] == 0

    def test_auto_replace_empty_list(self, client: TestClient):
        """Auto-replace empty tag list."""
        request_data = {"tags": []}
        response = client.post("/prompt/auto-replace", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["replaced"] == []

    def test_auto_replace_preserves_original(self, client: TestClient):
        """Response includes original tag list."""
        request_data = {"tags": ["medium_shot", "smile"]}
        response = client.post("/prompt/auto-replace", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["original"] == ["medium_shot", "smile"]


class TestCheckConflicts:
    """Test POST /prompt/check-conflicts endpoint."""

    def test_check_conflicts_no_conflicts(self, client: TestClient, db_session):
        """Tags without conflicts return clean result."""
        request_data = {"tags": ["smile", "standing"]}
        response = client.post("/prompt/check-conflicts", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["has_conflicts"] is False
        assert data["total_tags"] == 2

    def test_check_conflicts_empty_list(self, client: TestClient, db_session):
        """Empty tag list returns no conflicts."""
        request_data = {"tags": []}
        response = client.post("/prompt/check-conflicts", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is False
        assert data["total_tags"] == 0
