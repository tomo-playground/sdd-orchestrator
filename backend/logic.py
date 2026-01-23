from __future__ import annotations

import random
import re
import shutil
import subprocess
import time
from typing import Any

import edge_tts
import httpx
from fastapi import HTTPException
from google.genai import types
from PIL import Image

from schemas import (
    OverlaySettings,
    PostCardSettings,
    PromptRewriteRequest,
    PromptSplitRequest,
    SceneGenerateRequest,
    SceneValidateRequest,
    StoryboardRequest,
    VideoRequest,
)

# Import configuration from centralized config module
from config import (
    API_PUBLIC_URL,
    ASSETS_DIR,
    AUDIO_DIR,
    AVATAR_DIR,
    CACHE_DIR,
    CACHE_TTL_SECONDS,
    CANDIDATE_DIR,
    IMAGE_DIR,
    OUTPUT_DIR,
    OVERLAY_DIR,
    SD_BASE_URL,
    SD_LORAS_URL,
    SD_MODELS_URL,
    SD_OPTIONS_URL,
    SD_TIMEOUT_SECONDS,
    SD_TXT2IMG_URL,
    VIDEO_DIR,
    WD14_MODEL_DIR,
    WD14_THRESHOLD,
    gemini_client,
    logger,
    template_env,
)

# Keyword functions imported from services
from services.keywords import (
    expand_synonyms,
    filter_prompt_tokens,
    format_keyword_context,
    load_keyword_map,
    load_keyword_suggestions,
    load_keywords_file,
    load_known_keywords,
    normalize_prompt_token,
    reset_keyword_cache,
    save_keywords_file,
    update_keyword_suggestions,
)

# Validation functions imported from services
from services.validation import (
    cache_key_for_validation,
    compare_prompt_to_tags,
    gemini_predict_tags,
    load_wd14_model,
    resolve_image_mime,
    wd14_predict_tags,
)

# Rendering functions imported from services
from services.rendering import (
    apply_post_overlay_mask,
    calculate_post_layout_metrics,
    compose_post_frame,
    create_overlay_image,
    load_avatar_image,
    render_subtitle_image,
    resolve_overlay_frame,
    resolve_subtitle_font_path,
    _get_font,
    _get_font_from_path,
    _build_post_meta,
    _random_meta_values,
)

# Image functions imported from services
from services.image import decode_data_url, load_image_bytes

# Avatar functions imported from services
from services.avatar import avatar_filename, ensure_avatar_file

# Prompt functions imported from services
from services.prompt import (
    is_scene_token,
    merge_prompt_tokens,
    normalize_negative_prompt,
    normalize_prompt_tokens,
    split_prompt_tokens,
)

# Utility functions imported from services
from services.utils import (
    get_audio_duration,
    parse_json_payload,
    scrub_payload,
    to_edge_tts_rate,
    wrap_text,
)

# Video functions imported from services
from services.video import (
    calculate_scene_durations,
    calculate_speed_params,
    clean_script_for_tts,
    generate_video_filename,
    sanitize_project_name,
)

# --- Core Business Logic (Moved from Endpoints) ---

def logic_create_storyboard(request: StoryboardRequest) -> dict:
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini key missing")
    try:
        template = template_env.get_template("create_storyboard.j2")
        system_instruction = (
            "SYSTEM: You are a professional storyboarder and scriptwriter. "
            "Write concise, punchy scripts in the requested language (max 40 chars). "
            "No emojis. Use ONLY the allowed keywords list for image_prompt tags. "
            "Do not invent new tags. Return raw JSON only."
        )
        rendered = template.render(
            topic=request.topic,
            duration=request.duration,
            style=request.style,
            structure=request.structure,
            language=request.language,
            keyword_context=format_keyword_context(),
        )
        res = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=f"{system_instruction}\n\n{rendered}",
        )
        scenes = json.loads(res.text.strip().replace("```json", "").replace("```", ""))
        for scene in scenes:
            raw_prompt = scene.get("image_prompt", "")
            if not raw_prompt:
                continue
            filtered = filter_prompt_tokens(raw_prompt)
            if not filtered:
                logger.warning("No allowed keywords in scene prompt; using normalized original.")
                filtered = normalize_prompt_tokens(raw_prompt)
            scene["image_prompt"] = filtered
        return {"scenes": scenes}
    except Exception as exc:
        logger.exception("Storyboard generation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

async def logic_generate_scene_image(request: SceneGenerateRequest) -> dict:
    if not request.prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    cleaned_prompt = normalize_prompt_tokens(request.prompt)
    cleaned_negative = normalize_negative_prompt(request.negative_prompt or "")
    payload = {
        "prompt": cleaned_prompt,
        "negative_prompt": cleaned_negative,
        "steps": request.steps,
        "cfg_scale": request.cfg_scale,
        "sampler_name": request.sampler_name,
        "seed": request.seed,
        "width": request.width,
        "height": request.height,
        "override_settings": {
            "CLIP_stop_at_last_layers": max(1, int(request.clip_skip)),
        },
        "override_settings_restore_afterwards": True,
    }
    if request.enable_hr:
        payload.update({
            "enable_hr": True,
            "hr_scale": request.hr_scale,
            "hr_upscaler": request.hr_upscaler,
            "hr_second_pass_steps": request.hr_second_pass_steps,
            "denoising_strength": request.denoising_strength,
        })
    logger.info("🧾 [Scene Gen Payload] %s", payload)

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(SD_TXT2IMG_URL, json=payload, timeout=SD_TIMEOUT_SECONDS)
            res.raise_for_status()
            data = res.json()
            img = data.get("images", [None])[0]
            if not img:
                raise HTTPException(status_code=500, detail="No image returned")
            return {"image": img}
    except httpx.HTTPError as exc:
        logger.exception("Scene generation failed")
        raise HTTPException(status_code=502, detail=str(exc))

def logic_validate_scene_image(request: SceneValidateRequest) -> dict:
    try:
        image_bytes = load_image_bytes(request.image_b64)
        mode = request.mode.lower().strip() if request.mode else "wd14"
        cache_key = cache_key_for_validation(image_bytes, request.prompt or "", mode)
        cache_file = CACHE_DIR / f"image_validate_{cache_key}.json"
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < CACHE_TTL_SECONDS:
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
                cached["cached"] = True
                return cached
        image = Image.open(io.BytesIO(image_bytes))
        if mode == "gemini":
            tags = gemini_predict_tags(image)
        else:
            tags = wd14_predict_tags(image, WD14_THRESHOLD)
        comparison = compare_prompt_to_tags(request.prompt or "", tags)
        total = len(comparison["matched"]) + len(comparison["missing"])
        match_rate = (len(comparison["matched"]) / total) if total else 0.0
        known_keywords = load_known_keywords()
        unknown_tags = []
        for item in tags[:50]:
            name = normalize_prompt_token(item["tag"])
            if not name:
                continue
            if name not in known_keywords:
                unknown_tags.append(name)
        update_keyword_suggestions(unknown_tags)
        result = {
            "mode": mode,
            "match_rate": match_rate,
            "matched": comparison["matched"],
            "missing": comparison["missing"],
            "extra": comparison["extra"],
            "tags": tags[:20],
            "unknown_tags": unknown_tags[:20],
        }
        cache_file.write_text(json.dumps(result, ensure_ascii=False))
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Scene image validation failed")
        raise HTTPException(status_code=500, detail="Image validation failed") from exc

def logic_rewrite_prompt(request: PromptRewriteRequest) -> dict:
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini key missing")
    if not request.base_prompt or not request.scene_prompt:
        raise HTTPException(status_code=400, detail="Base prompt and scene prompt are required")

    cache_key = hashlib.sha256(
        f"{request.base_prompt}|{request.scene_prompt}|{request.style}|{request.mode}".encode()
    ).hexdigest()
    cache_file = CACHE_DIR / f"prompt_{cache_key}.json"
    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < CACHE_TTL_SECONDS:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            return {"prompt": cached.get("prompt", "")}

    if request.mode == "scene":
        instruction = (
            "Convert SCENE into Stable Diffusion tag-style prompt. "
            "Use comma-separated short tags, no full sentences. "
            "Include camera/shot keywords if implied. Return ONLY the tags."
        )
    else:
        instruction = (
            "Rewrite a Stable Diffusion prompt. Keep the identity/style tokens from BASE. "
            "Replace scene/action/pose with SCENE. Preserve any <lora:...> tags. "
            "Return ONLY the final comma-separated prompt, no explanations."
        )
    user_input = (
        f"BASE: {request.base_prompt}\n"
        f"SCENE: {request.scene_prompt}\n"
        f"STYLE: {request.style}\n"
    )
    try:
        res = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=f"{instruction}\n\n{user_input}",
        )
        text = res.text.strip().replace("```", "")
        if request.mode == "scene":
            cache_file.write_text(json.dumps({"prompt": text}, ensure_ascii=False))
            return {"prompt": text}
        base_tokens = split_prompt_tokens(request.base_prompt)
        base_core = [
            token for token in base_tokens
            if "<lora:" in token.lower() or not is_scene_token(token)
        ]
        rewritten_tokens = split_prompt_tokens(text)
        final_prompt = merge_prompt_tokens(base_core, rewritten_tokens)
        cache_file.write_text(json.dumps({"prompt": final_prompt}, ensure_ascii=False))
        return {"prompt": final_prompt}
    except Exception as exc:
        logger.exception("Prompt rewrite failed")
        raise HTTPException(status_code=500, detail=str(exc))

def logic_split_prompt(request: PromptSplitRequest) -> dict:
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini key missing")
    if not request.example_prompt:
        raise HTTPException(status_code=400, detail="Example prompt is required")

    instruction = (
        "Split the EXAMPLE prompt into BASE and SCENE for Stable Diffusion. "
        "BASE should keep identity/style/LoRA tokens. SCENE should keep action, pose, "
        "camera, and background. Return ONLY JSON with keys base_prompt and scene_prompt."
    )
    user_input = f"EXAMPLE: {request.example_prompt}\nSTYLE: {request.style}\n"
    try:
        res = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=f"{instruction}\n\n{user_input}",
        )
        text = res.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(text)
        return {
            "base_prompt": data.get("base_prompt", ""),
            "scene_prompt": data.get("scene_prompt", ""),
        }
    except Exception as exc:
        logger.exception("Prompt split failed")
        raise HTTPException(status_code=500, detail=str(exc))

async def logic_create_video(request: VideoRequest) -> dict:
    logger.info("Video build started: %s", request.project_name)

    project_id = f"build_{int(time.time())}"
    temp_dir = IMAGE_DIR / project_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    safe_project_name = sanitize_project_name(request.project_name)
    video_filename = generate_video_filename(safe_project_name, request.layout_style)
    video_path = VIDEO_DIR / video_filename
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)

    font_path = resolve_subtitle_font_path(request.subtitle_font)

    try:
        input_args: list[str] = []
        num_scenes = len(request.scenes)
        transition_dur, tts_padding, speed_multiplier = calculate_speed_params(
            request.speed_multiplier or 1.0
        )
        tts_rate = to_edge_tts_rate(speed_multiplier)
        tts_valid: list[bool] = []
        tts_durations: list[float] = []

        use_post_layout = request.layout_style == "post"
        meta_rng = random.Random(time.time_ns())
        full_views, full_time = _random_meta_values(meta_rng)
        post_views, post_time = _random_meta_values(meta_rng)
        avatar_file = None
        if request.overlay_settings:
            request.overlay_settings.likes_count = full_views
            request.overlay_settings.posted_time = full_time
            avatar_file = await ensure_avatar_file(request.overlay_settings.avatar_key)
            if avatar_file:
                request.overlay_settings.avatar_file = avatar_file
        post_avatar_file = None
        if request.post_card_settings:
            post_avatar_file = await ensure_avatar_file(request.post_card_settings.avatar_key)
        subtitle_lines: list[list[str]] = []
        for i, scene in enumerate(request.scenes):
            img_path = temp_dir / f"scene_{i}.png"
            tts_path = temp_dir / f"tts_{i}.mp3"

            image_bytes = load_image_bytes(scene.image_url)
            raw_script = scene.script or ""
            logger.info(f"Scene {i}: script='{raw_script}', len={len(raw_script)}")
            clean_script = clean_script_for_tts(raw_script)
            if use_post_layout:
                try:
                    overlay_settings = request.overlay_settings or OverlaySettings()
                    post_settings = request.post_card_settings or PostCardSettings(
                        channel_name=overlay_settings.channel_name,
                        avatar_key=overlay_settings.avatar_key,
                        caption=overlay_settings.caption,
                    )
                    composed = compose_post_frame(
                        image_bytes, request.width, request.height,
                        post_settings.channel_name, post_settings.caption,
                        "", font_path, post_avatar_file or avatar_file,
                        post_views, post_time,
                    )
                    composed.save(img_path, "PNG")
                except Exception:
                    img_path.write_bytes(image_bytes)
            else:
                img_path.write_bytes(image_bytes)

            if request.include_subtitles:
                wrapped_script = wrap_text(clean_script, width=20, max_lines=2)
                lines = [line for line in wrapped_script.splitlines() if line.strip()]
                subtitle_lines.append(lines)
            else:
                subtitle_lines.append([])

            has_valid_tts = False
            tts_duration = 0.0
            if raw_script.strip():
                try:
                    voice = request.narrator_voice
                    logger.info(f"TTS 생성 시도: voice={voice}, script={raw_script[:50]}...")
                    communicate = edge_tts.Communicate(raw_script, voice, rate=tts_rate)
                    await communicate.save(str(tts_path))
                    if tts_path.exists() and tts_path.stat().st_size > 0:
                        has_valid_tts = True
                        tts_duration = get_audio_duration(tts_path)
                        logger.info(f"TTS 생성 성공: duration={tts_duration}s")
                    else:
                        logger.warning(f"TTS 파일 생성 실패 또는 빈 파일")
                except Exception as e:
                    logger.error(f"TTS 생성 에러: {e}")
            else:
                logger.warning(f"Scene {i}: 스크립트가 비어있어 TTS 생략")

            input_args.extend(["-loop", "1", "-i", str(img_path)])
            if has_valid_tts:
                input_args.extend(["-i", str(tts_path)])
            else:
                input_args.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])

            tts_valid.append(has_valid_tts)
            tts_durations.append(tts_duration)

        scene_durations = calculate_scene_durations(
            request.scenes, tts_valid, tts_durations, speed_multiplier, tts_padding
        )

        filters: list[str] = []
        out_w, out_h = (request.width, request.height)

        post_layout_metrics = None
        if use_post_layout:
            # Use shared layout calculation (synced with compose_post_frame)
            post_layout_metrics = calculate_post_layout_metrics(out_w, out_h)

        subtitle_base_idx = num_scenes * 2
        if request.include_subtitles:
            for i in range(num_scenes):
                subtitle_path = temp_dir / f"subtitle_{i}.png"
                subtitle_img = render_subtitle_image(
                    subtitle_lines[i], out_w, out_h, font_path,
                    use_post_layout, post_layout_metrics,
                )
                subtitle_img.save(subtitle_path, "PNG")
                input_args.extend(["-loop", "1", "-i", str(subtitle_path)])

        for i in range(num_scenes):
            v_idx = i * 2
            base_dur = scene_durations[i]
            clip_dur = base_dur + (transition_dur if i < num_scenes - 1 else 0)
            motion_frames = max(1, int(clip_dur * 25))

            if use_post_layout:
                if request.motion_style == "slow_zoom":
                    filters.append(
                        f"[{v_idx}:v]scale={out_w}:{out_h},"
                        f"zoompan=z='min(zoom+0.0008,1.08)':d={motion_frames}:s={out_w}x{out_h}:fps=25"
                        f"[v{i}_base]"
                    )
                else:
                    filters.append(f"[{v_idx}:v]scale={out_w}:{out_h}[v{i}_base]")
            else:
                # Full 레이아웃: 정사각형 이미지 + 블러 배경
                filters.append(f"[{v_idx}:v]split=2[v{i}_in_1][v{i}_in_2]")
                bg_scale = (
                    f"[v{i}_in_1]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
                    f"crop={out_w}:{out_h},boxblur=40:20"
                )
                if request.motion_style == "slow_zoom":
                    filters.append(
                        f"{bg_scale},"
                        f"zoompan=z='min(zoom+0.0008,1.08)':d={motion_frames}:s={out_w}x{out_h}:fps=25"
                        f"[v{i}_bg]"
                    )
                else:
                    filters.append(f"{bg_scale}[v{i}_bg]")

                # 정사각형 이미지 (가로 100%, 상단 배치로 영상 강조)
                sq_size = out_w  # 100% 너비
                sq_y = int(out_h * 0.10)  # 상단 10% (헤더 아래)
                filters.append(
                    f"[v{i}_in_2]scale={sq_size}:{sq_size}:force_original_aspect_ratio=decrease,"
                    f"pad={sq_size}:{sq_size}:(ow-iw)/2:(oh-ih)/2[v{i}_sq]"
                )
                filters.append(
                    f"[v{i}_bg][v{i}_sq]overlay=0:{sq_y}:format=auto[v{i}_base]"
                )

            if request.include_subtitles:
                sub_idx = subtitle_base_idx + i
                filters.append(f"[{sub_idx}:v]scale={out_w}:{out_h},format=rgba[sub{i}]")
                filters.append(f"[v{i}_base][sub{i}]overlay=0:0:format=auto[v{i}_text]")
                filters.append(
                    f"[v{i}_text]trim=duration={clip_dur},setpts=PTS-STARTPTS[v{i}_raw]"
                )
            else:
                filters.append(f"[v{i}_base]trim=duration={clip_dur},setpts=PTS-STARTPTS[v{i}_raw]")

        for i in range(num_scenes):
            a_idx = i * 2 + 1
            clip_dur = scene_durations[i] + (transition_dur if i < num_scenes - 1 else 0)
            filters.append(
                f"[{a_idx}:a]aresample=44100,aformat=channel_layouts=stereo,apad,"
                f"atrim=duration={clip_dur},asetpts=PTS-STARTPTS[a{i}_raw]"
            )

        if num_scenes > 1:
            curr_v, curr_a, acc_offset = "[v0_raw]", "[a0_raw]", 0
            for i in range(1, num_scenes):
                prev_dur = scene_durations[i - 1]
                acc_offset += prev_dur
                filters.append(
                    f"{curr_v}[v{i}_raw]xfade=transition=fade:duration={transition_dur}:offset={acc_offset}[v{i}_m]"
                )
                curr_v = f"[v{i}_m]"
                filters.append(
                    f"{curr_a}[a{i}_raw]acrossfade=d={transition_dur}:o=1:c1=tri:c2=tri[a{i}_m]"
                )
                curr_a = f"[a{i}_m]"
            map_v, map_a = curr_v, curr_a
            total_dur = acc_offset + scene_durations[-1]
        else:
            map_v, map_a = "[v0_raw]", "[a0_raw]"
            total_dur = scene_durations[0] if scene_durations else 0

        next_input_idx = num_scenes * 2
        if request.include_subtitles:
            next_input_idx += num_scenes

        if request.overlay_settings:
            if request.layout_style == "post":
                logger.info("Overlay disabled for post layout to avoid double UI.")
            else:
                overlay_path = temp_dir / "overlay.png"
                resolve_overlay_frame(request.overlay_settings, out_w, out_h, overlay_path, request.layout_style)
                if request.layout_style == "post":
                    apply_post_overlay_mask(overlay_path, out_w, out_h)
                input_args.extend(["-i", str(overlay_path)])
                if request.layout_style == "full":
                    filters.append(
                        f"[{next_input_idx}:v]scale={out_w}:{out_h},format=rgba,"
                        f"colorchannelmixer=aa=1.6[ovr]"
                    )
                else:
                    filters.append(f"[{next_input_idx}:v]scale={out_w}:{out_h}[ovr]")
                filters.append(f"{map_v}[ovr]overlay=0:0[vid_o]")
                map_v = "[vid_o]"
                next_input_idx += 1

        bgm_path = AUDIO_DIR / request.bgm_file if request.bgm_file else None
        if bgm_path and bgm_path.exists():
            input_args.extend(["-i", str(bgm_path)])
            filters.append(
                f"[{next_input_idx}:a]volume=0.15,afade=t=out:st={max(0, total_dur-2)}:d=2[bgm_f]"
            )
            filters.append(f"{map_a}[bgm_f]amix=inputs=2:duration=first:dropout_transition=2[a_f]")
            map_a = "[a_f]"

        filter_complex_str = ";".join(filters)
        cmd = ["ffmpeg", "-y"] + input_args + [
            "-filter_complex", filter_complex_str,
            "-map", map_v,
            "-map", map_a,
            "-s", f"{out_w}x{out_h}",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "medium",
            "-c:a", "aac",
            "-b:a", "192k",
            str(video_path),
        ]

        logger.info("Running FFmpeg")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("FFmpeg failed: %s", result.stderr)
            raise Exception(result.stderr)

        shutil.rmtree(temp_dir)

        return {"video_url": f"{API_PUBLIC_URL}/outputs/videos/{video_filename}"}
    except Exception as exc:
        logger.exception("Video Create Error")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise HTTPException(status_code=500, detail=str(exc))
