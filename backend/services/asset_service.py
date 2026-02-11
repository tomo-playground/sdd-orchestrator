from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from config import logger
from models.media_asset import MediaAsset
from services.storage import get_storage


class AssetService:
    """Service for managing media assets with storage and database registry."""

    def __init__(self, db: Session):
        self.db = db

    def _get_storage(self):
        """Get storage instance dynamically to avoid import-time issues."""
        return get_storage()

    def get_asset_url(self, storage_key: str) -> str:
        """Get the public URL for a given storage key."""
        return self._get_storage().get_url(storage_key)

    def register_asset(
        self,
        file_name: str,
        file_type: str,
        storage_key: str,
        owner_type: str | None = None,
        owner_id: int | None = None,
        is_temp: bool = False,
        file_size: int | None = None,
        mime_type: str | None = None,
        checksum: str | None = None,
        # Backward compatibility args (ignored or mapped)
        project_id: int | None = None,
        storyboard_id: int | None = None,
        scene_id: int | None = None,
    ) -> MediaAsset:
        """Create a MediaAsset record in the database."""

        # Backward compatibility mapping
        if project_id:
            owner_type = "project"
            owner_id = project_id
        elif storyboard_id:
            owner_type = "storyboard"
            owner_id = storyboard_id
        elif scene_id:
            owner_type = "scene"
            owner_id = scene_id

        asset = MediaAsset(
            owner_type=owner_type,
            owner_id=owner_id,
            is_temp=is_temp,
            file_type=file_type,
            storage_key=storage_key,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            checksum=checksum,
        )
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)

        owner_info = f" ({owner_type}:{owner_id})" if owner_type else " (Orphan)"
        logger.info(f"📊 [Asset Registry] Registered {file_type}: {file_name}{owner_info} ID: {asset.id}")
        return asset

    def save_character_preview(self, character_id: int, image_bytes: bytes) -> MediaAsset:
        """Save a character preview image to storage and register it in the DB."""
        import hashlib

        digest = hashlib.sha1(image_bytes).hexdigest()[:16]
        file_name = f"character_{character_id}_preview_{digest}.png"
        storage_key = f"characters/{character_id}/preview/{file_name}"
        self._get_storage().save(storage_key, image_bytes, content_type="image/png")
        return self.register_asset(
            file_name=file_name,
            file_type="image",
            storage_key=storage_key,
            owner_type="character",
            owner_id=character_id,
            file_size=len(image_bytes),
            mime_type="image/png",
        )

    def save_background_image(self, background_id: int, image_bytes: bytes, mime_type: str = "image/png") -> MediaAsset:
        """Save a background reference image to storage and register it in the DB."""
        import hashlib

        ext = "png" if "png" in mime_type else "jpg" if "jpeg" in mime_type or "jpg" in mime_type else "webp"
        digest = hashlib.sha1(image_bytes).hexdigest()[:16]
        file_name = f"background_{background_id}_{digest}.{ext}"
        storage_key = f"backgrounds/{background_id}/{file_name}"
        self._get_storage().save(storage_key, image_bytes, content_type=mime_type)
        return self.register_asset(
            file_name=file_name,
            file_type="image",
            storage_key=storage_key,
            owner_type="background",
            owner_id=background_id,
            file_size=len(image_bytes),
            mime_type=mime_type,
        )

    def save_scene_image(
        self, image_bytes: bytes, project_id: int, group_id: int, storyboard_id: int, scene_id: int, file_name: str
    ) -> MediaAsset:
        """Save a scene image to storage and register it in the DB."""
        # Define hierarchical key
        storage_key = f"projects/{project_id}/groups/{group_id}/storyboards/{storyboard_id}/images/{file_name}"

        # Save to storage (MinIO/S3 or Local)
        self._get_storage().save(storage_key, image_bytes, content_type="image/png")

        # Register in DB with generic relationship
        return self.register_asset(
            file_name=file_name,
            file_type="image",
            storage_key=storage_key,
            owner_type="scene",
            owner_id=scene_id,
            file_size=len(image_bytes),
            mime_type="image/png",
        )

    def save_rendered_video(
        self, video_path: Path, project_id: int, group_id: int, storyboard_id: int, file_name: str
    ) -> MediaAsset:
        """Save a rendered video to storage and register it in the DB."""
        storage_key = f"projects/{project_id}/groups/{group_id}/storyboards/{storyboard_id}/videos/{file_name}"

        file_size = video_path.stat().st_size
        with open(video_path, "rb") as f:
            self._get_storage().save(storage_key, f, content_type="video/mp4")

        return self.register_asset(
            file_name=file_name,
            file_type="video",
            storage_key=storage_key,
            owner_type="storyboard",
            owner_id=storyboard_id,
            file_size=file_size,
            mime_type="video/mp4",
        )

    @staticmethod
    def ensure_shared_assets():
        """Synchronize repository assets (audio, fonts) to centralized storage."""
        from config import ASSETS_DIR, AUDIO_DIR, FONTS_DIR, OVERLAY_DIR

        storage = get_storage()

        # Mapping: local_dir -> storage_prefix
        sync_map = {
            AUDIO_DIR: "shared/audio/",
            FONTS_DIR: "shared/fonts/",
            OVERLAY_DIR: "shared/overlay/",
            ASSETS_DIR / "references": "shared/references/",
            ASSETS_DIR / "poses": "shared/poses/",
        }

        for local_dir, prefix in sync_map.items():
            if not local_dir.exists():
                logger.warning(f"⚠️ [Asset Sync] Local directory not found: {local_dir}")
                continue

            for file_path in local_dir.iterdir():
                if file_path.is_file() and not file_path.name.startswith("."):
                    storage_key = f"{prefix}{file_path.name}"
                    if not storage.exists(storage_key):
                        try:
                            with open(file_path, "rb") as f:
                                # Determine content type
                                ext = file_path.suffix.lower()
                                if ext == ".mp3":
                                    content_type = "audio/mpeg"
                                elif ext in (".ttf", ".otf", ".ttc"):
                                    content_type = "font/ttf"
                                elif ext in (".png", ".jpg", ".jpeg"):
                                    content_type = "image/png"
                                else:
                                    content_type = "application/octet-stream"

                                storage.save(storage_key, f, content_type=content_type)
                            logger.info(f"📤 [Asset Sync] Uploaded to shared storage: {storage_key}")
                        except Exception as e:
                            logger.error(f"❌ [Asset Sync] Failed to sync {file_path.name}: {e}")

        logger.info("✅ [Asset Sync] Shared assets synchronization complete")
