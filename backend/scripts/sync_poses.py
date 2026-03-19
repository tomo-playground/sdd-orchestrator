import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(os.getcwd())

from services.storage import get_storage


def sync_poses():
    storage = get_storage()
    pose_dir = Path("backend/assets/poses")

    if not pose_dir.exists():
        print(f"Error: Directory {pose_dir} not found")
        return

    for file_path in pose_dir.glob("*.png"):
        storage_key = f"shared/poses/{file_path.name}"
        with open(file_path, "rb") as f:
            storage.save(storage_key, f, content_type="image/png")
        print(f"Synced {file_path.name} -> {storage_key}")


if __name__ == "__main__":
    sync_poses()
