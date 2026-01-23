from __future__ import annotations

import hashlib
import io
import json
import time

import httpx
from fastapi import HTTPException
from PIL import Image

from schemas import (
    PromptRewriteRequest,
    PromptSplitRequest,
    SceneGenerateRequest,
    SceneValidateRequest,
    StoryboardRequest,
    VideoRequest,
)

from config import (
    CACHE_DIR,
    CACHE_TTL_SECONDS,
    SD_TIMEOUT_SECONDS,
    SD_TXT2IMG_URL,
    WD14_THRESHOLD,
    gemini_client,
    logger,
    template_env,
)

from services.keywords import (
    filter_prompt_tokens,
    format_keyword_context,
    load_known_keywords,
    normalize_prompt_token,
    update_keyword_suggestions,
)

from services.validation import (
    cache_key_for_validation,
    compare_prompt_to_tags,
    gemini_predict_tags,
    wd14_predict_tags,
)

from services.image import load_image_bytes

from services.prompt import (
    is_scene_token,
    merge_prompt_tokens,
    normalize_negative_prompt,
    normalize_prompt_tokens,
    split_prompt_tokens,
)

from services.video import VideoBuilder

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
    """Create a video from scenes using VideoBuilder."""
    try:
        builder = VideoBuilder(request)
        return await builder.build()
    except Exception as exc:
        logger.exception("Video Create Error")
        raise HTTPException(status_code=500, detail=str(exc))
