from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

from config import logger


class BaseStorage(ABC):
    """Abstract base class for storage drivers."""

    @abstractmethod
    def save(self, key: str, body: bytes | BinaryIO, content_type: str | None = None) -> str:
        """Save a file and return its public URL or storage path."""
        pass

    @abstractmethod
    def get_url(self, key: str) -> str:
        """Get the public URL for a given storage key."""
        pass

    @abstractmethod
    def get_local_path(self, key: str) -> Path:
        """Download to local cache if needed and return the local path."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a file exists in storage."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a file from storage."""
        pass

    @abstractmethod
    def list_prefix(self, prefix: str) -> list[str]:
        """List all keys under a given prefix."""
        pass


class S3Storage(BaseStorage):
    """S3 compatible storage driver (MinIO, AWS S3)."""

    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket_name: str, public_url: str, cache_dir: Path):
        try:
            import boto3
        except ImportError:
            raise ImportError(
                "S3 스토리지를 사용하려면 boto3 패키지가 필요합니다. 'pip install boto3'를 실행해주세요."
            ) from None

        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
        )
        self.bucket_name = bucket_name
        self.public_url = public_url
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def save(self, key: str, body: bytes | BinaryIO, content_type: str | None = None) -> str:
        from botocore.exceptions import ClientError
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        try:
            self.s3.put_object(Bucket=self.bucket_name, Key=key, Body=body, **extra_args)
            return self.get_url(key)
        except ClientError as e:
            logger.error(f"S3 저장 실패: {e}")
            raise

    def get_url(self, key: str) -> str:
        # Assuming bucket is public-read as per our setup
        return f"{self.public_url}/{self.bucket_name}/{key}"

    def get_local_path(self, key: str) -> Path:
        """Ensure the file is in local cache for FFmpeg processing."""
        from botocore.exceptions import ClientError
        local_path = self.cache_dir / key
        if local_path.exists():
            return local_path

        local_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.s3.download_file(self.bucket_name, key, str(local_path))
            return local_path
        except ClientError as e:
            logger.error(f"S3 다운로드 실패: {e}")
            raise

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            self.s3.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def delete(self, key: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            self.s3.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            logger.error(f"S3 삭제 실패: {e}")
            return False

    def list_prefix(self, prefix: str) -> list[str]:
        """List all keys under a given prefix in S3."""
        from botocore.exceptions import ClientError
        try:
            paginator = self.s3.get_paginator("list_objects_v2")
            keys = []
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        keys.append(obj["Key"])
            return keys
        except ClientError as e:
            logger.error(f"S3 목록 조회 실패: {e}")
            return []


class LocalStorage(BaseStorage):
    """Local file system storage driver."""

    def __init__(self, base_dir: Path, public_url: str):
        self.base_dir = base_dir
        self.public_url = public_url
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, key: str, body: bytes | BinaryIO, content_type: str | None = None) -> str:
        file_path = self.base_dir / key
        file_path.parent.mkdir(parents=True, exist_ok=True)

        data = body.read() if hasattr(body, "read") else body
        with open(file_path, "wb") as f:
            f.write(data)
        return self.get_url(key)

    def get_url(self, key: str) -> str:
        return f"{self.public_url}/outputs/{key}"

    def get_local_path(self, key: str) -> Path:
        return self.base_dir / key

    def exists(self, key: str) -> bool:
        return (self.base_dir / key).exists()

    def delete(self, key: str) -> bool:
        file_path = self.base_dir / key
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def list_prefix(self, prefix: str) -> list[str]:
        """List all keys under a given prefix in local file system."""
        scan_dir = self.base_dir / prefix
        if not scan_dir.exists():
            return []

        keys = []
        for file_path in scan_dir.rglob("*"):
            if file_path.is_file():
                # Return paths relative to base_dir to match storage key format
                keys.append(str(file_path.relative_to(self.base_dir)))
        return keys


# Global storage instance
storage: BaseStorage = None


def initialize_storage():
    """Initialize the global storage instance based on config."""
    global storage
    from config import (
        API_PUBLIC_URL,
        MINIO_ACCESS_KEY,
        MINIO_BUCKET,
        MINIO_ENDPOINT,
        MINIO_SECRET_KEY,
        OUTPUT_DIR,
        STORAGE_MODE,
        STORAGE_PUBLIC_URL,
        logger,
    )

    if STORAGE_MODE == "s3":
        storage = S3Storage(
            endpoint_url=MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            bucket_name=MINIO_BUCKET,
            public_url=STORAGE_PUBLIC_URL,
            cache_dir=OUTPUT_DIR / "cache",
        )
        logger.info("📦 Storage initialized: S3 (MinIO)")
    else:
        storage = LocalStorage(base_dir=OUTPUT_DIR, public_url=API_PUBLIC_URL)
        logger.info("📦 Storage initialized: Local FileSystem")
    return storage
