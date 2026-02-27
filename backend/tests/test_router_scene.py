import base64
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

@pytest.fixture
def mock_asset_service():
    with patch("routers.scene.AssetService") as m:
        yield m

def test_store_scene_image_endpoint(mock_asset_service):
    # Prepare mock image and request
    image_data = base64.b64encode(b"fake-image-bytes").decode("utf-8")
    request_data = {
        "image_b64": f"data:image/png;base64,{image_data}",
        "project_id": 1,
        "group_id": 1,
        "storyboard_id": 1,
        "scene_id": 1,
        "file_name": "scene_1.png"
    }

    # Mock behavior
    mock_service_instance = mock_asset_service.return_value
    mock_service_instance.save_scene_image.return_value = MagicMock(
        storage_key="projects/1/groups/1/storyboards/1/images/scene_1.png"
    )
    mock_service_instance.get_asset_url.return_value = "http://minio/scene_1.png"

    response = client.post("/api/v1/image/store", json=request_data)

    resp_json = response.json()
    assert response.status_code == 200
    assert resp_json["url"] == "http://minio/scene_1.png"
    # assert resp_json["asset_id"] is not None # If we implemented asset_id return
    mock_service_instance.save_scene_image.assert_called_once()
