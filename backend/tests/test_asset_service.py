from unittest.mock import MagicMock, patch

import pytest

from models.media_asset import MediaAsset
from services.asset_service import AssetService


@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def mock_storage():
    with patch("services.asset_service.storage") as m:
        yield m

class TestAssetService:
    def test_register_asset(self, mock_db):
        service = AssetService(mock_db)
        asset = service.register_asset(
            file_name="test.png",
            file_type="image",
            storage_key="key/path",
            project_id=1
        )

        assert isinstance(asset, MediaAsset)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_save_scene_image(self, mock_db, mock_storage):
        service = AssetService(mock_db)
        mock_storage.save.return_value = "http://minio/test.png"

        asset = service.save_scene_image(
            image_bytes=b"data",
            project_id=1,
            group_id=2,
            storyboard_id=3,
            scene_id=4,
            file_name="scene.png"
        )

        expected_key = "projects/1/groups/2/storyboards/3/images/scene.png"
        mock_storage.save.assert_called_once_with(expected_key, b"data", content_type="image/png")
        assert asset.storage_key == expected_key
        assert asset.file_type == "image"
