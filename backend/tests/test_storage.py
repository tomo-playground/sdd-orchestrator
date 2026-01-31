from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.storage import LocalStorage, S3Storage


@pytest.fixture
def temp_output_dir(tmp_path):
    d = tmp_path / "outputs"
    d.mkdir()
    return d

class TestLocalStorage:
    def test_save_and_exists(self, temp_output_dir):
        storage = LocalStorage(base_dir=temp_output_dir, public_url="http://test")
        key = "test_project/test.txt"
        content = b"hello world"

        url = storage.save(key, content)
        assert storage.exists(key)
        assert (temp_output_dir / key).read_bytes() == content
        assert url == "http://test/outputs/test_project/test.txt"

    def test_delete(self, temp_output_dir):
        storage = LocalStorage(base_dir=temp_output_dir, public_url="http://test")
        key = "delete_me.txt"
        storage.save(key, b"content")
        assert storage.exists(key)

        assert storage.delete(key)
        assert not storage.exists(key)

    def test_get_local_path(self, temp_output_dir):
        storage = LocalStorage(base_dir=temp_output_dir, public_url="http://test")
        key = "path/test.txt"
        path = storage.get_local_path(key)
        assert path == temp_output_dir / key

class TestS3Storage:
    @patch("boto3.client")
    def test_save(self, mock_boto):
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3

        storage = S3Storage(
            endpoint_url="http://minio",
            access_key="key",
            secret_key="secret",
            bucket_name="bucket",
            public_url="http://pub",
            cache_dir=Path("/tmp/cache")
        )

        key = "projects/1/test.png"
        storage.save(key, b"data", content_type="image/png")

        mock_s3.put_object.assert_called_once_with(
            Bucket="bucket",
            Key=key,
            Body=b"data",
            ContentType="image/png"
        )
