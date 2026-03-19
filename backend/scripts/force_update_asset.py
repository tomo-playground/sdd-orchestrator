import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(os.getcwd())

from services.storage import get_storage


def force_update_pose():
    storage = get_storage()
    local_path = Path("assets/poses/standing_arms_up.png")
    storage_key = "shared/poses/standing_arms_up.png"

    if not local_path.exists():
        print(f"Error: Local file {local_path} not found")
        return

    with open(local_path, "rb") as f:
        storage.save(storage_key, f, content_type="image/png")

    print(f"Successfully force-updated {storage_key} in storage.")


if __name__ == "__main__":
    force_update_pose()
