"""Upload validation: MIME whitelist, size limit, and magic byte checks."""

from __future__ import annotations

from fastapi import HTTPException, UploadFile

from config import MAX_IMAGE_UPLOAD_BYTES

ALLOWED_IMAGE_MIMES: set[str] = {"image/png", "image/jpeg", "image/webp", "image/gif"}

# Magic byte signatures for image formats
_MAGIC_BYTES: dict[str, list[bytes]] = {
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/webp": [b"RIFF"],  # RIFF....WEBP
    "image/gif": [b"GIF87a", b"GIF89a"],
}


async def validate_image_upload(file: UploadFile) -> bytes:
    """Validate and read an uploaded image file.

    Checks:
    1. Content-Type is in ALLOWED_IMAGE_MIMES
    2. File size <= MAX_IMAGE_UPLOAD_BYTES
    3. Magic bytes match declared MIME type

    Returns the raw image bytes on success.
    Raises HTTPException(400) on any validation failure.
    """
    mime = file.content_type or ""
    if mime not in ALLOWED_IMAGE_MIMES:
        raise HTTPException(
            status_code=400,
            detail=f"허용되지 않는 파일 형식입니다: {mime}. 허용: {', '.join(sorted(ALLOWED_IMAGE_MIMES))}",
        )

    data = await file.read()

    if len(data) > MAX_IMAGE_UPLOAD_BYTES:
        mb_limit = MAX_IMAGE_UPLOAD_BYTES / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"파일 크기가 {mb_limit:.0f}MB 제한을 초과합니다.",
        )

    if not _check_magic_bytes(data, mime):
        raise HTTPException(
            status_code=400,
            detail="파일 내용이 선언된 MIME 타입과 일치하지 않습니다.",
        )

    return data


def _check_magic_bytes(data: bytes, mime: str) -> bool:
    """Return True if the first bytes match the expected magic bytes for mime."""
    signatures = _MAGIC_BYTES.get(mime)
    if not signatures:
        return True  # Unknown MIME — skip check
    return any(data[: len(sig)] == sig for sig in signatures)
