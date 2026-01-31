import os
import sys
import unittest

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from services.asset_service import AssetService
from services.storage import initialize_storage, storage


class TestSharedAssets(unittest.TestCase):
    def setUp(self):
        # Initialize storage (local mode for test)
        os.environ["STORAGE_MODE"] = "local"
        initialize_storage()

    def test_ensure_shared_assets(self):
        # Run sync
        AssetService.ensure_shared_assets()

        # Verify BGM files are in shared/audio/
        bgm_keys = storage.list_prefix("shared/audio/")
        self.assertTrue(len(bgm_keys) > 0, "BGM keys should be listed")

        # Verify Font files are in shared/fonts/
        font_keys = storage.list_prefix("shared/fonts/")
        self.assertTrue(len(font_keys) > 0, "Font keys should be listed")

        print(f"✅ Found {len(bgm_keys)} BGMs and {len(font_keys)} fonts in storage")

    def test_list_prefix_nested(self):
        # Create a dummy nested file
        storage.save("test/nested/file.txt", b"hello")
        keys = storage.list_prefix("test/nested/")
        self.assertIn("test/nested/file.txt", keys)
        storage.delete("test/nested/file.txt")

if __name__ == "__main__":
    unittest.main()
