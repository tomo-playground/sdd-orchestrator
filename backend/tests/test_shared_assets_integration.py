import os
import unittest

from services.asset_service import AssetService
from services.storage import get_storage, initialize_storage


class TestSharedAssets(unittest.TestCase):
    def setUp(self):
        # Initialize storage (local mode for test)
        os.environ["STORAGE_MODE"] = "local"
        initialize_storage()

    def test_ensure_shared_assets(self):
        # Run sync
        AssetService.ensure_shared_assets()

        store = get_storage()

        # Verify BGM files are in shared/audio/
        bgm_keys = store.list_prefix("shared/audio/")
        self.assertTrue(len(bgm_keys) > 0, "BGM keys should be listed")

        # Verify Font files are in shared/fonts/
        font_keys = store.list_prefix("shared/fonts/")
        self.assertTrue(len(font_keys) > 0, "Font keys should be listed")

        print(f"Found {len(bgm_keys)} BGMs and {len(font_keys)} fonts in storage")

    def test_list_prefix_nested(self):
        store = get_storage()
        # Create a dummy nested file
        store.save("test/nested/file.txt", b"hello")
        keys = store.list_prefix("test/nested/")
        self.assertIn("test/nested/file.txt", keys)
        store.delete("test/nested/file.txt")

if __name__ == "__main__":
    unittest.main()
