"""Tests for backgrounds router endpoints."""

import struct
import zlib
from unittest.mock import patch

from fastapi.testclient import TestClient


def make_tiny_png() -> bytes:
    """Create a minimal 1x1 white PNG."""

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = zlib.compress(b"\x00\xff\xff\xff")
    idat = chunk(b"IDAT", raw)
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


def _create_bg(client: TestClient, **overrides) -> dict:
    """Helper to create a background via POST."""
    payload = {"name": "Test BG", "tags": ["indoor"], "category": "interior"}
    payload.update(overrides)
    resp = client.post("/backgrounds", json=payload)
    assert resp.status_code == 201
    return resp.json()


class TestBackgroundsRouter:
    """Test background CRUD operations."""

    def test_create_background(self, client: TestClient):
        """POST /backgrounds creates a new background and returns 201."""
        payload = {
            "name": "Sakura Park",
            "tags": ["outdoor", "cherry_blossom"],
            "category": "nature",
            "weight": 0.5,
        }
        resp = client.post("/backgrounds", json=payload)
        assert resp.status_code == 201
        data = resp.json()

        assert data["name"] == "Sakura Park"
        assert data["tags"] == ["outdoor", "cherry_blossom"]
        assert data["category"] == "nature"
        assert data["weight"] == 0.5
        assert data["is_system"] is False
        assert data["id"] is not None
        assert data["image_url"] is None

    def test_list_backgrounds(self, client: TestClient):
        """GET /backgrounds returns all non-deleted backgrounds."""
        _create_bg(client, name="BG Alpha")
        _create_bg(client, name="BG Beta")

        resp = client.get("/backgrounds")
        assert resp.status_code == 200
        data = resp.json()
        names = {bg["name"] for bg in data}
        assert "BG Alpha" in names
        assert "BG Beta" in names

    def test_get_background(self, client: TestClient):
        """GET /backgrounds/{id} returns the correct background."""
        created = _create_bg(client, name="Library Room")
        bg_id = created["id"]

        resp = client.get(f"/backgrounds/{bg_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == bg_id
        assert data["name"] == "Library Room"

    def test_update_background(self, client: TestClient):
        """PUT /backgrounds/{id} updates fields and returns the result."""
        created = _create_bg(client, name="Old Name", weight=0.3)
        bg_id = created["id"]

        resp = client.put(
            f"/backgrounds/{bg_id}",
            json={"name": "New Name", "weight": 0.7},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "New Name"
        assert data["weight"] == 0.7

    def test_soft_delete_and_restore(self, client: TestClient):
        """DELETE soft-deletes; GET returns 404; restore brings it back."""
        created = _create_bg(client, name="Deletable BG")
        bg_id = created["id"]

        # Soft delete
        del_resp = client.delete(f"/backgrounds/{bg_id}")
        assert del_resp.status_code == 200
        assert del_resp.json() == {"ok": True, "deleted": "Deletable BG"}

        # GET should 404
        assert client.get(f"/backgrounds/{bg_id}").status_code == 404

        # List should exclude deleted
        listed = client.get("/backgrounds").json()
        assert all(bg["id"] != bg_id for bg in listed)

        # Restore
        restore_resp = client.post(f"/backgrounds/{bg_id}/restore")
        assert restore_resp.status_code == 200
        assert restore_resp.json()["name"] == "Deletable BG"

        # Should appear in list again
        listed_after = client.get("/backgrounds").json()
        assert any(bg["id"] == bg_id for bg in listed_after)

    def test_filter_by_category(self, client: TestClient):
        """GET /backgrounds?category= returns only matching backgrounds."""
        _create_bg(client, name="City Alley", category="urban")
        _create_bg(client, name="Forest Path", category="nature")

        resp = client.get("/backgrounds", params={"category": "urban"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "City Alley"

    def test_search(self, client: TestClient):
        """GET /backgrounds?search= performs case-insensitive name search."""
        _create_bg(client, name="Classroom A")
        _create_bg(client, name="Rooftop")

        resp = client.get("/backgrounds", params={"search": "class"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Classroom A"

    def test_categories_endpoint(self, client: TestClient):
        """GET /backgrounds/categories returns distinct category list."""
        _create_bg(client, name="BG 1", category="indoor")
        _create_bg(client, name="BG 2", category="outdoor")
        _create_bg(client, name="BG 3", category="indoor")

        resp = client.get("/backgrounds/categories")
        assert resp.status_code == 200
        cats = resp.json()
        assert set(cats) == {"indoor", "outdoor"}

    def test_upload_image(self, client: TestClient, db_session):
        """POST /backgrounds/{id}/upload-image stores image and returns url."""
        from models.media_asset import MediaAsset

        created = _create_bg(client, name="Uploadable BG")
        bg_id = created["id"]

        # Pre-create a real MediaAsset so FK constraint is satisfied
        asset = MediaAsset(
            file_type="image",
            storage_key=f"backgrounds/{bg_id}/test.png",
            file_name="test.png",
            file_size=100,
            mime_type="image/png",
            owner_type="background",
            owner_id=bg_id,
        )
        db_session.add(asset)
        db_session.commit()
        db_session.refresh(asset)

        # Mock AssetService.save_background_image to return the real DB record,
        # and mock storage.get_url to avoid real MinIO calls.
        with (
            patch("routers.backgrounds.AssetService") as mock_svc_cls,
            patch("services.storage.get_storage") as mock_storage,
        ):
            mock_svc_cls.return_value.save_background_image.return_value = asset
            mock_storage.return_value.get_url.return_value = (
                "http://minio:9000/backgrounds/test.png"
            )

            png_bytes = make_tiny_png()
            resp = client.post(
                f"/backgrounds/{bg_id}/upload-image",
                files={"file": ("bg.png", png_bytes, "image/png")},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["image_asset_id"] == asset.id
        assert data["image_url"] is not None
