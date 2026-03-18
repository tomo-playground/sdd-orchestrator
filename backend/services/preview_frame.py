"""Frame preview: Pillow-based scene frame composition (no FFmpeg)."""

from __future__ import annotations

import hashlib
import io

from PIL import Image
from sqlalchemy.orm import Session

from config import (
    DEFAULT_SCENE_TEXT_FONT,
    FONTS_DIR,
    MAX_PREVIEW_IMAGE_BYTES,
)
from schemas import (
    FrameLayoutInfo,
    SceneFramePreviewRequest,
    SceneFramePreviewResponse,
)
from services.asset_service import AssetService
from services.storage import get_storage


async def preview_scene_frame(
    req: SceneFramePreviewRequest,
    db: Session,
) -> SceneFramePreviewResponse:
    """Compose a single scene frame preview (Pillow only, no FFmpeg)."""
    from services.image import (
        analyze_text_region_brightness,
        detect_face,
        load_image_bytes,
    )
    from services.rendering import (
        calculate_optimal_font_size,
        compose_post_frame,
        render_scene_text_image,
    )

    image_bytes = load_image_bytes(req.image_url)
    if len(image_bytes) > MAX_PREVIEW_IMAGE_BYTES:
        raise ValueError(f"이미지 크기가 제한({MAX_PREVIEW_IMAGE_BYTES // (1024 * 1024)}MB)을 초과합니다.")
    font_name = req.scene_text_font or DEFAULT_SCENE_TEXT_FONT
    font_path = str(FONTS_DIR / font_name)

    layout_info = FrameLayoutInfo()

    if req.layout_style == "post":
        frame = compose_post_frame(
            image_bytes=image_bytes,
            width=req.width,
            height=req.height,
            channel_name=req.channel_name or "",
            caption=req.caption or "",
            subtitle_text=req.script if req.include_scene_text else "",
            font_path=font_path,
        )
        src_img = Image.open(io.BytesIO(image_bytes))
        face = detect_face(src_img)
        layout_info.face_detected = face is not None
        src_img.close()

    else:
        src_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        frame = src_img.resize((req.width, req.height), Image.LANCZOS)

        if req.include_scene_text and req.script.strip():
            lines = req.script.strip().split("\n")
            font_size = calculate_optimal_font_size(req.script, 40)
            layout_info.font_size = font_size

            brightness = analyze_text_region_brightness(frame, 0.85)
            layout_info.text_brightness = brightness

            text_overlay = render_scene_text_image(
                lines=lines,
                width=req.width,
                height=req.height,
                font_path=font_path,
                use_post_layout=False,
                post_layout_metrics=None,
                font_size_override=font_size,
                background_image=frame,
            )
            frame.paste(text_overlay, (0, 0), text_overlay)
            text_overlay.close()

        src_img.close()

    # Save to storage
    buf = io.BytesIO()
    frame.convert("RGB").save(buf, format="PNG")
    frame.close()
    png_bytes = buf.getvalue()

    digest = hashlib.sha256(png_bytes).hexdigest()[:16]
    file_name = f"frame_preview_{digest}.png"
    storage_key = f"previews/frames/{file_name}"

    storage = get_storage()
    storage.save(storage_key, png_bytes, content_type="image/png")

    asset_svc = AssetService(db)
    asset = asset_svc.register_asset(
        file_name=file_name,
        file_type="image",
        storage_key=storage_key,
        owner_type="frame_preview",
        is_temp=True,
        file_size=len(png_bytes),
        mime_type="image/png",
        checksum=AssetService.compute_checksum(png_bytes),
    )

    return SceneFramePreviewResponse(
        preview_url=asset.url,
        temp_asset_id=asset.id,
        layout_info=layout_info,
    )
