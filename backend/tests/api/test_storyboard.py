"""Tests for storyboard management API endpoints."""

from conftest import create_test_storyboard
from fastapi.testclient import TestClient


def _make_scene(scene_id: int = 0, **overrides) -> dict:
    """Build a scene dict with defaults."""
    base = {
        "scene_id": scene_id,
        "script": f"Scene {scene_id} script",
        "speaker": "Narrator",
        "duration": 3.0,
        "image_prompt": "1girl, school_uniform",
        "image_prompt_ko": "소녀, 교복",
        "width": 512,
        "height": 768,
    }
    base.update(overrides)
    return base


def testcreate_test_storyboard(client: TestClient):
    """Test creating a storyboard."""
    data = create_test_storyboard(client)
    assert data["status"] == "success"
    assert "storyboard_id" in data


def test_list_storyboards(client: TestClient):
    """Test listing storyboards."""
    response = client.get("/storyboards")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_with_scene_count(client: TestClient):
    """Test that list includes scene_count and image_count."""
    scenes = [_make_scene(0), _make_scene(1, image_url="/img/test.png")]
    create_test_storyboard(client, scenes=scenes)

    resp = client.get("/storyboards")
    items = resp.json()
    assert len(items) >= 1
    item = items[-1]
    assert item["scene_count"] == 2
    assert item["image_count"] == 1


def test_get_storyboard_with_scenes(client: TestClient):
    """Test GET /storyboards/{id} returns full storyboard with scenes."""
    scenes = [
        _make_scene(0, speaker="Narrator", duration=2.5),
        _make_scene(1, speaker="Character", duration=4.0, image_url="/img/s1.png"),
    ]
    data = create_test_storyboard(client, title="Full Test", scenes=scenes)
    sb_id = data["storyboard_id"]

    resp = client.get(f"/storyboards/{sb_id}")
    assert resp.status_code == 200

    body = resp.json()
    assert body["id"] == sb_id
    assert body["title"] == "Full Test"
    assert len(body["scenes"]) == 2
    assert body["scenes"][0]["speaker"] == "Narrator"
    assert body["scenes"][1]["duration"] == 4.0


def test_get_storyboard_not_found(client: TestClient):
    """Test GET /storyboards/{id} returns 404 for missing storyboard."""
    resp = client.get("/storyboards/99999")
    assert resp.status_code == 404


def test_save_with_extended_fields(client: TestClient):
    """Test saving and retrieving extended scene fields (SD settings moved to group_config)."""
    scenes = [_make_scene(
        0,
        negative_prompt="bad_hands, blurry",
        context_tags={"expression": ["smile"], "camera": "close-up"},
    )]
    data = create_test_storyboard(client, title="Extended", scenes=scenes)
    sb_id = data["storyboard_id"]

    resp = client.get(f"/storyboards/{sb_id}")
    body = resp.json()
    sc = body["scenes"][0]

    assert sc["negative_prompt"] == "bad_hands, blurry"
    assert sc["context_tags"]["expression"] == ["smile"]


def test_update_storyboard(client: TestClient):
    """Test PUT /storyboards/{id} replaces scenes."""
    data = create_test_storyboard(client, title="Original", scenes=[_make_scene(0)])
    sb_id = data["storyboard_id"]

    # Update with new scenes
    update_resp = client.put(f"/storyboards/{sb_id}", json={
        "title": "Updated Title",
        "description": "updated desc",
        "scenes": [_make_scene(0, script="New script"), _make_scene(1, script="Second scene")],
    })
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "success"

    # Verify update
    resp = client.get(f"/storyboards/{sb_id}")
    body = resp.json()
    assert body["title"] == "Updated Title"
    assert len(body["scenes"]) == 2
    assert body["scenes"][0]["script"] == "New script"


def test_delete_storyboard(client: TestClient):
    """Test DELETE /storyboards/{id}."""
    data = create_test_storyboard(client, title="ToDelete", scenes=[_make_scene(0)])
    sb_id = data["storyboard_id"]

    del_resp = client.delete(f"/storyboards/{sb_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"

    # Verify deleted
    get_resp = client.get(f"/storyboards/{sb_id}")
    assert get_resp.status_code == 404
