from unittest.mock import MagicMock, patch

import pytest

from schemas import VideoRequest, VideoScene
from services.video import VideoBuilder


@pytest.fixture
def mock_asset_service():
    with patch("services.video.AssetService") as m:
        yield m

@pytest.fixture
def mock_storage():
    with patch("services.video.storage") as m:
        yield m

@pytest.mark.anyio
async def test_video_builder_uses_storage_and_asset_service(mock_asset_service, mock_storage, tmp_path):
    # Setup mock request
    scene = VideoScene(image_url="http://test/image.png", script="test")
    request = VideoRequest(
        scenes=[scene],
        storyboard_id=1,
        storyboard_title="test_video",
        project_id=1,
        group_id=1
    )

    # We need to mock some internal helper functions that VideoBuilder uses
    with patch("services.video.VideoBuilder._setup_avatars"), \
         patch("services.video.VideoBuilder._process_scenes"), \
         patch("services.video.VideoBuilder._calculate_durations"), \
         patch("services.video.VideoBuilder._build_filters"), \
         patch("services.video.VideoBuilder._encode"), \
         patch("services.video.VideoBuilder._cleanup"):

        builder = VideoBuilder(request)

        # Simulate video file creation
        builder.video_path = tmp_path / "test.mp4"
        builder.video_path.touch()

        # Mock AssetService behavior
        mock_asset_service_instance = mock_asset_service.return_value
        mock_asset_service_instance.save_rendered_video.return_value = MagicMock(
            storage_key="test/video.mp4"
        )
        mock_asset_service_instance.get_asset_url.return_value = "http://minio/test.mp4"

        result = await builder.build()

        # Assertions
        mock_asset_service_instance.save_rendered_video.assert_called_once()
        assert result["video_url"] == "http://minio/test.mp4"
