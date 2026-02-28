"""Tests for backend-complete store pipeline (Phase 22).

Covers:
- resolve_project_group_ids (storyboard helpers)
- _sync_store_image / store_image_to_db (image_gen_pipeline)
- run_image_gen (end-to-end async pipeline)
- ImageProgressEvent serialization
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest

from models.media_asset import MediaAsset
from models.scene import Scene
from models.storyboard import Storyboard
from schemas import ImageProgressEvent, SceneGenerateRequest
from services.image_gen_pipeline import (
    _sync_store_image,
    run_image_gen,
    store_image_to_db,
)
from services.image_progress import (
    ImageGenStage,
    create_image_task,
)
from services.storyboard.helpers import resolve_project_group_ids


# ────────────────────────────────────────────
# resolve_project_group_ids
# ────────────────────────────────────────────


class TestResolveProjectGroupIds:
    """resolve_project_group_ids: storyboard_id -> (project_id, group_id)."""

    def test_resolve_project_group_ids_success(self, db_session):
        """storyboard_id -> (project_id, group_id) 정상 조회."""
        # Group(id=1, project_id=1) already seeded by conftest
        sb = Storyboard(title="test", group_id=1)
        db_session.add(sb)
        db_session.commit()

        result = resolve_project_group_ids(db_session, sb.id)
        assert result == (1, 1)

    def test_resolve_project_group_ids_not_found(self, db_session):
        """없는 storyboard_id -> None."""
        result = resolve_project_group_ids(db_session, 9999)
        assert result is None


# ────────────────────────────────────────────
# Backend Store pipeline
# ────────────────────────────────────────────


class TestBackendStore:
    """_sync_store_image, store_image_to_db, ImageProgressEvent tests."""

    def _make_scene(self, db_session, storyboard_id: int, client_id: str = "cli-1") -> Scene:
        """Helper: create a Scene attached to a storyboard."""
        scene = Scene(
            storyboard_id=storyboard_id,
            client_id=client_id,
            order=0,
            script="test",
        )
        db_session.add(scene)
        db_session.commit()
        return scene

    def _make_asset(self, db_session, storage_key: str = "test/img.png") -> MediaAsset:
        """Helper: create a real MediaAsset row to satisfy FK constraints."""
        asset = MediaAsset(
            file_type="image",
            storage_key=storage_key,
            file_name="test.png",
        )
        db_session.add(asset)
        db_session.commit()
        return asset

    # -- Test 3 --
    def test_store_image_to_db_updates_scene(self, db_session):
        """_sync_store_image: scene.image_asset_id 업데이트 확인."""
        sb = Storyboard(title="store-test", group_id=1)
        db_session.add(sb)
        db_session.commit()

        scene = self._make_scene(db_session, sb.id, client_id="c-store")
        real_asset = self._make_asset(db_session, "projects/1/images/store.png")

        @contextmanager
        def fake_db_session():
            yield db_session

        with (
            patch(
                "services.image_gen_pipeline.get_db_session",
                fake_db_session,
            ),
            patch(
                "services.image_gen_pipeline.AssetService"
            ) as MockAssetService,
            patch(
                "services.image_gen_pipeline.decode_data_url",
                return_value=b"\x89PNG\r\n\x1a\n" + b"\x00" * 100,
            ),
        ):
            mock_instance = MockAssetService.return_value
            mock_instance.save_scene_image.return_value = real_asset
            mock_instance.get_asset_url.return_value = "http://minio/test.png"

            url, asset_id = _sync_store_image(
                "base64data", sb.id, scene.id, "c-store"
            )

        assert url == "http://minio/test.png"
        assert asset_id == real_asset.id

        db_session.refresh(scene)
        assert scene.image_asset_id == real_asset.id

    # -- Test 4 --
    def test_store_image_to_db_client_id_fallback(self, db_session):
        """client_id fallback -- scene_id가 stale일 때 client_id로 해결."""
        sb = Storyboard(title="fallback-test", group_id=1)
        db_session.add(sb)
        db_session.commit()

        # Create a scene, note its ID, then soft-delete it
        old_scene = self._make_scene(db_session, sb.id, client_id="cli-fb")
        stale_id = old_scene.id
        from datetime import datetime, timezone

        old_scene.deleted_at = datetime.now(timezone.utc)
        db_session.commit()

        # Create a new scene with a different client_id
        new_scene = Scene(
            storyboard_id=sb.id,
            client_id="cli-fb-new",
            order=1,
            script="replacement",
        )
        db_session.add(new_scene)
        db_session.commit()

        real_asset = self._make_asset(db_session, "projects/1/images/fallback.png")

        @contextmanager
        def fake_db_session():
            yield db_session

        with (
            patch(
                "services.image_gen_pipeline.get_db_session",
                fake_db_session,
            ),
            patch(
                "services.image_gen_pipeline.AssetService"
            ) as MockAssetService,
            patch(
                "services.image_gen_pipeline.decode_data_url",
                return_value=b"\x89PNG" + b"\x00" * 100,
            ),
        ):
            mock_instance = MockAssetService.return_value
            mock_instance.save_scene_image.return_value = real_asset
            mock_instance.get_asset_url.return_value = "http://minio/fb.png"

            # Pass stale scene_id + new client_id
            url, asset_id = _sync_store_image(
                "base64data", sb.id, stale_id, "cli-fb-new"
            )

        assert url == "http://minio/fb.png"
        assert asset_id == real_asset.id

        db_session.refresh(new_scene)
        assert new_scene.image_asset_id == real_asset.id

    # -- Test 5 --
    async def test_store_image_to_db_no_storyboard_id(self):
        """storyboard_id 없으면 (None, None) 즉시 반환."""
        request = SceneGenerateRequest(
            prompt="test", storyboard_id=None, scene_id=1
        )
        result = await store_image_to_db("base64data", request)
        assert result == (None, None)

    # -- Test 6 --
    def test_image_progress_event_serialization(self):
        """ImageProgressEvent에 image_url/image_asset_id 포함."""
        event = ImageProgressEvent(
            task_id="t1",
            stage="completed",
            image_url="http://minio/test.png",
            image_asset_id=42,
        )
        data = event.model_dump()
        assert data["image_url"] == "http://minio/test.png"
        assert data["image_asset_id"] == 42
        assert data["stage"] == "completed"
        assert data["task_id"] == "t1"


# ────────────────────────────────────────────
# run_image_gen end-to-end
# ────────────────────────────────────────────


class TestRunImageGen:
    """run_image_gen: async pipeline end-to-end tests."""

    def _make_request(self, **overrides) -> SceneGenerateRequest:
        defaults = dict(
            prompt="masterpiece, 1girl",
            storyboard_id=1,
            scene_id=1,
            client_id="cli-test",
        )
        defaults.update(overrides)
        return SceneGenerateRequest(**defaults)

    # -- Test 7 --
    async def test_run_image_gen_stores_on_complete(self):
        """COMPLETED 시 result에 image_url 존재."""
        task = create_image_task()
        request = self._make_request()

        fake_result = {
            "image": "base64imagedata",
            "used_prompt": "masterpiece, 1girl",
        }

        with (
            patch(
                "services.image_gen_pipeline.generate_and_validate",
                new_callable=AsyncMock,
                return_value=fake_result,
            ),
            patch(
                "services.image_gen_pipeline.store_image_to_db",
                new_callable=AsyncMock,
                return_value=("http://minio/stored.png", 99),
            ),
            patch(
                "services.image_gen_pipeline.has_critical_failure",
                return_value=False,
            ),
        ):
            await run_image_gen(task.task_id, request)

        assert task.stage == ImageGenStage.COMPLETED
        assert task.result is not None
        assert task.result["image_url"] == "http://minio/stored.png"
        assert task.result["image_asset_id"] == 99

    # -- Test 8 --
    async def test_run_image_gen_fallback_on_store_failure(self):
        """저장 실패 시 image_url=None, base64 보존, COMPLETED 유지."""
        task = create_image_task()
        request = self._make_request()

        fake_result = {
            "image": "base64preserved",
            "used_prompt": "masterpiece, 1girl",
        }

        with (
            patch(
                "services.image_gen_pipeline.generate_and_validate",
                new_callable=AsyncMock,
                return_value=fake_result,
            ),
            patch(
                "services.image_gen_pipeline.store_image_to_db",
                new_callable=AsyncMock,
                side_effect=Exception("MinIO connection failed"),
            ),
            patch(
                "services.image_gen_pipeline.has_critical_failure",
                return_value=False,
            ),
        ):
            await run_image_gen(task.task_id, request)

        # Pipeline should complete even if storage fails
        assert task.stage == ImageGenStage.COMPLETED
        assert task.result is not None
        assert task.result["image"] == "base64preserved"
        assert "image_url" not in task.result
