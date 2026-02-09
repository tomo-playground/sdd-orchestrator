"""
Lab service -- experiment execution and tag effectiveness aggregation.

Phase 1 Integration: Uses unified image_generation_core.py for V3 Prompt Engine.
"""

from __future__ import annotations

import base64
import uuid
from collections import defaultdict
from io import BytesIO
from typing import Any

from PIL import Image
from sqlalchemy.orm import Session

from config import LAB_BATCH_MAX_SIZE, LAB_DEFAULT_SD_STEPS, logger
from models.lab import LabExperiment
from services.validation import compare_prompt_to_tags, wd14_predict_tags


async def run_experiment(
    db: Session,
    target_tags: list[str],
    group_id: int,
    character_id: int | None = None,
    negative_prompt: str | None = None,
    sd_params: dict | None = None,
    seed: int | None = None,
    experiment_type: str = "tag_render",
    scene_description: str | None = None,
    notes: str | None = None,
    batch_id: str | None = None,
) -> LabExperiment:
    """
    Run a single experiment using V3 Prompt Engine.

    Phase 1 Integration: Uses unified image_generation_core.py
    - Applies V3 Prompt Builder (Character LoRA + Scene Tags + Style LoRAs)
    - Applies Style Profile (Quality Tags + Negative Prompt)
    - Stores final_prompt and loras_applied metadata
    """
    from services.image_generation_core import generate_image_with_v3

    params = sd_params or {}
    steps = params.get("steps", LAB_DEFAULT_SD_STEPS)
    cfg_scale = params.get("cfg_scale", 7.0)
    sampler = params.get("sampler", "DPM++ 2M Karras")
    width = params.get("width", 512)
    height = params.get("height", 768)
    actual_seed = seed if seed and seed > 0 else -1

    # Initial prompt (for reference)
    initial_prompt = ", ".join(target_tags)

    experiment = LabExperiment(
        batch_id=batch_id,
        experiment_type=experiment_type,
        status="running",
        character_id=character_id,
        group_id=group_id,
        prompt_used=initial_prompt,  # Original prompt
        negative_prompt=negative_prompt,
        target_tags=target_tags,
        sd_params={
            "steps": steps,
            "cfg_scale": cfg_scale,
            "sampler": sampler,
            "width": width,
            "height": height,
        },
        seed=actual_seed,
        scene_description=scene_description,
        notes=notes,
    )
    db.add(experiment)
    db.flush()

    try:
        # V3 Prompt Engine + SD Generation
        result = await generate_image_with_v3(
            db=db,
            prompt=target_tags,
            character_id=character_id,
            group_id=group_id,
            sd_params={
                "steps": steps,
                "cfg_scale": cfg_scale,
                "sampler": sampler,
                "width": width,
                "height": height,
                "seed": actual_seed,
                "negative_prompt": negative_prompt or "",
            },
            mode="lab",
        )

        # Store V3 metadata
        experiment.final_prompt = result.final_prompt
        experiment.loras_applied = result.loras_applied
        experiment.seed = result.seed

        # Decode image and validate
        image_bytes = base64.b64decode(result.image)
        image = Image.open(BytesIO(image_bytes))

        save_experiment_image(experiment.id, image_bytes)

        # WD14 Validation
        tags = wd14_predict_tags(image)
        comparison = compare_prompt_to_tags(initial_prompt, tags)
        match_rate = _calc_match_rate(comparison)

        experiment.status = "completed"
        experiment.match_rate = match_rate
        experiment.wd14_result = _build_wd14_result(comparison, tags)

        # Log warnings from V3 (if any)
        if result.warnings:
            logger.warning(
                "[Lab] Experiment %s warnings: %s",
                experiment.id, result.warnings
            )

    except Exception as e:
        logger.error("[Lab] Experiment %s failed: %s", experiment.id, e)
        experiment.status = "failed"
        experiment.notes = (experiment.notes or "") + f"\nError: {e}"

    db.commit()
    return experiment




def _calc_match_rate(comparison: dict) -> float:
    """Calculate match rate from comparison result."""
    matched = comparison.get("matched", [])
    missing = comparison.get("missing", [])
    total = len(matched) + len(missing)
    return len(matched) / total if total > 0 else 0.0


def _build_wd14_result(comparison: dict, tags: list[dict]) -> dict:
    """Build WD14 result dict for DB storage."""
    return {
        "matched": comparison.get("matched", []),
        "missing": comparison.get("missing", []),
        "extra": comparison.get("extra", []),
        "partial_matched": comparison.get("partial_matched", []),
        "skipped": comparison.get("skipped", []),
        "raw_tags": [
            {"tag": t["tag"], "score": t["score"]} for t in tags[:30]
        ],
    }


def save_experiment_image(
    experiment_id: int, image_bytes: bytes,
) -> None:
    """Save experiment image to storage (best-effort)."""
    try:
        from services.storage import get_storage

        storage = get_storage()
        key = f"lab/experiments/{experiment_id}.png"
        storage.save(key, image_bytes, content_type="image/png")
    except Exception as e:
        logger.warning(
            "[Lab] Failed to save image for experiment %s: %s",
            experiment_id, e,
        )


async def run_batch(
    db: Session,
    target_tags: list[str],
    group_id: int,
    count: int = 5,
    character_id: int | None = None,
    negative_prompt: str | None = None,
    sd_params: dict | None = None,
    seeds: list[int] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Run a batch of experiments with the same tags (V3 Prompt Engine)."""
    count = min(count, LAB_BATCH_MAX_SIZE)
    bid = uuid.uuid4().hex[:12]
    results: list[LabExperiment] = []

    for i in range(count):
        seed = seeds[i] if seeds and i < len(seeds) else -1
        exp = await run_experiment(
            db=db,
            target_tags=target_tags,
            group_id=group_id,
            character_id=character_id,
            negative_prompt=negative_prompt,
            sd_params=sd_params,
            seed=seed,
            batch_id=bid,
            notes=notes,
        )
        results.append(exp)

    completed = sum(1 for r in results if r.status == "completed")
    failed = sum(1 for r in results if r.status == "failed")

    return {
        "batch_id": bid,
        "total": count,
        "completed": completed,
        "failed": failed,
        "experiments": results,
    }


def aggregate_tag_effectiveness(db: Session) -> dict[str, Any]:
    """Aggregate tag effectiveness from completed lab experiments."""
    experiments = (
        db.query(LabExperiment)
        .filter(LabExperiment.status == "completed")
        .filter(LabExperiment.wd14_result.isnot(None))
        .all()
    )

    tag_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"use_count": 0, "match_count": 0},
    )

    for exp in experiments:
        if not exp.target_tags or not exp.wd14_result:
            continue
        matched = set(exp.wd14_result.get("matched", []))
        for tag in exp.target_tags:
            tag_stats[tag]["use_count"] += 1
            if tag in matched:
                tag_stats[tag]["match_count"] += 1

    items = [
        {
            "tag_name": name,
            "tag_id": 0,
            "use_count": stats["use_count"],
            "match_count": stats["match_count"],
            "effectiveness": (
                stats["match_count"] / stats["use_count"]
                if stats["use_count"] > 0
                else 0.0
            ),
        }
        for name, stats in sorted(
            tag_stats.items(),
            key=lambda x: x[1]["use_count"],
            reverse=True,
        )
    ]

    total = len(experiments)
    avg_rate = (
        sum(e.match_rate for e in experiments if e.match_rate is not None)
        / total
        if total > 0
        else None
    )

    return {
        "items": items,
        "total_experiments": total,
        "avg_match_rate": avg_rate,
    }


async def compose_and_run(
    db: Session,
    scene_description: str,
    group_id: int,
    character_id: int,
    negative_prompt: str | None = None,
    sd_params: dict | None = None,
    seed: int | None = None,
    notes: str | None = None,
) -> LabExperiment:
    """Scene Lab: run experiment with scene_description tags.

    V3 composition is handled inside run_experiment → generate_image_with_v3.
    No direct V3PromptBuilder call here (DRY).
    """
    from services.prompt.prompt import split_prompt_tokens

    target_tags = split_prompt_tokens(scene_description)

    return await run_experiment(
        db=db,
        target_tags=target_tags,
        group_id=group_id,
        character_id=character_id,
        negative_prompt=negative_prompt,
        sd_params=sd_params,
        seed=seed,
        experiment_type="scene_translate",
        scene_description=scene_description,
        notes=notes,
    )


def sync_to_engine(db: Session) -> int:
    """Sync lab effectiveness data to tag_effectiveness table."""
    from models.tag import Tag, TagEffectiveness

    report = aggregate_tag_effectiveness(db)
    synced = 0

    for item in report["items"]:
        tag = db.query(Tag).filter(Tag.name == item["tag_name"]).first()
        if not tag:
            continue

        te = db.query(TagEffectiveness).filter_by(tag_id=tag.id).first()
        if te:
            te.use_count = item["use_count"]
            te.match_count = item["match_count"]
            te.effectiveness = item["effectiveness"]
        else:
            te = TagEffectiveness(
                tag_id=tag.id,
                use_count=item["use_count"],
                match_count=item["match_count"],
                effectiveness=item["effectiveness"],
            )
            db.add(te)
        synced += 1

    db.commit()
    return synced
