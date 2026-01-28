"""Evaluation service for Mode A/B quality comparison.

This module implements the Quality Evaluation System (15.6) for comparing
Standard mode vs LoRA mode prompt quality using WD14 validation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from config import logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# ============================================================
# 15.6.1: Standard Test Prompt Set
# ============================================================

# 6 test scenarios covering simple → complex, close-up → full body, indoor → outdoor


@dataclass
class TestPrompt:
    """Definition of a standard test prompt."""

    name: str
    description: str
    tokens: list[str]
    subject: str = "1girl"


TEST_PROMPTS: dict[str, TestPrompt] = {
    # === 기본 (6개) ===
    "simple_portrait": TestPrompt(
        name="simple_portrait",
        description="Simple portrait (1 expression, upper body)",
        tokens=["smile", "upper body"],
    ),
    "full_body_pose": TestPrompt(
        name="full_body_pose",
        description="Full body with pose",
        tokens=["standing", "full body"],
    ),
    "action_scene": TestPrompt(
        name="action_scene",
        description="Action with outdoor setting",
        tokens=["waving", "outdoor", "sunny"],
    ),
    "complex_indoor": TestPrompt(
        name="complex_indoor",
        description="Complex indoor scene with action",
        tokens=["sitting", "classroom", "reading book", "window"],
    ),
    "emotional_close": TestPrompt(
        name="emotional_close",
        description="Emotional close-up with details",
        tokens=["crying", "close-up", "tears"],
    ),
    "multi_element": TestPrompt(
        name="multi_element",
        description="Multi-element complex scene",
        tokens=["running", "sunset", "wind", "school uniform", "from side"],
    ),
    # === 표정 (4개) ===
    "expr_angry": TestPrompt(
        name="expr_angry",
        description="Angry expression",
        tokens=["angry", "frown", "upper body"],
    ),
    "expr_surprised": TestPrompt(
        name="expr_surprised",
        description="Surprised expression",
        tokens=["surprised", "open mouth", "close-up"],
    ),
    "expr_blush": TestPrompt(
        name="expr_blush",
        description="Shy blushing expression",
        tokens=["blush", "looking away", "embarrassed"],
    ),
    "expr_laugh": TestPrompt(
        name="expr_laugh",
        description="Laughing expression",
        tokens=["laughing", "closed eyes", "happy"],
    ),
    # === 포즈 (4개) ===
    "pose_jumping": TestPrompt(
        name="pose_jumping",
        description="Dynamic jumping pose",
        tokens=["jumping", "arms up", "full body"],
    ),
    "pose_lying": TestPrompt(
        name="pose_lying",
        description="Lying down pose",
        tokens=["lying", "on back", "bed"],
    ),
    "pose_walking": TestPrompt(
        name="pose_walking",
        description="Walking pose",
        tokens=["walking", "street", "from behind"],
    ),
    "pose_leaning": TestPrompt(
        name="pose_leaning",
        description="Leaning against wall",
        tokens=["leaning", "against wall", "crossed arms"],
    ),
    # === 카메라 앵글 (3개) ===
    "angle_from_above": TestPrompt(
        name="angle_from_above",
        description="Bird's eye view",
        tokens=["from above", "looking up", "full body"],
    ),
    "angle_from_below": TestPrompt(
        name="angle_from_below",
        description="Low angle shot",
        tokens=["from below", "looking down", "standing"],
    ),
    "angle_dutch": TestPrompt(
        name="angle_dutch",
        description="Dutch angle dynamic shot",
        tokens=["dutch angle", "running", "action"],
    ),
    # === 환경 (4개) ===
    "env_cafe": TestPrompt(
        name="env_cafe",
        description="Cafe setting",
        tokens=["cafe", "sitting", "holding cup", "table"],
    ),
    "env_street": TestPrompt(
        name="env_street",
        description="Urban street setting",
        tokens=["street", "city", "walking", "crowd"],
    ),
    "env_beach": TestPrompt(
        name="env_beach",
        description="Beach setting",
        tokens=["beach", "ocean", "swimsuit", "sunny"],
    ),
    "env_forest": TestPrompt(
        name="env_forest",
        description="Forest setting",
        tokens=["forest", "trees", "sunlight", "nature"],
    ),
    # === 시간/날씨 (4개) ===
    "time_night": TestPrompt(
        name="time_night",
        description="Night scene with city lights",
        tokens=["night", "city lights", "standing", "from below"],
    ),
    "weather_rain": TestPrompt(
        name="weather_rain",
        description="Rainy day scene",
        tokens=["rain", "umbrella", "wet", "street"],
    ),
    "weather_snow": TestPrompt(
        name="weather_snow",
        description="Snowy winter scene",
        tokens=["snow", "winter clothes", "breath", "cold"],
    ),
    "time_golden": TestPrompt(
        name="time_golden",
        description="Golden hour lighting",
        tokens=["golden hour", "backlighting", "warm light", "outdoor"],
    ),
    # === 의상 (3개) ===
    "cloth_casual": TestPrompt(
        name="cloth_casual",
        description="Casual daily clothes",
        tokens=["t-shirt", "jeans", "casual", "standing"],
    ),
    "cloth_formal": TestPrompt(
        name="cloth_formal",
        description="Formal dress",
        tokens=["dress", "formal", "elegant", "full body"],
    ),
    "cloth_winter": TestPrompt(
        name="cloth_winter",
        description="Winter outfit",
        tokens=["coat", "scarf", "winter", "outdoor"],
    ),
    # === 소품/액션 (2개) ===
    "prop_phone": TestPrompt(
        name="prop_phone",
        description="Using smartphone",
        tokens=["holding phone", "looking at phone", "sitting"],
    ),
    "prop_book": TestPrompt(
        name="prop_book",
        description="Reading a book",
        tokens=["holding book", "reading", "glasses", "indoor"],
    ),
}


def get_test_prompts() -> dict[str, TestPrompt]:
    """Get all standard test prompts."""
    return TEST_PROMPTS.copy()


def get_test_prompt(name: str) -> TestPrompt | None:
    """Get a specific test prompt by name."""
    return TEST_PROMPTS.get(name)


# ============================================================
# 15.6.3: Evaluation Run Logic
# ============================================================

EvaluationMode = Literal["standard", "lora"]


@dataclass
class EvaluationRequest:
    """Request for running evaluation tests."""

    test_names: list[str]
    character_id: int | None = None
    modes: list[EvaluationMode] | None = None
    repetitions: int = 3


@dataclass
class EvaluationResult:
    """Result of a single evaluation run."""

    test_name: str
    mode: EvaluationMode
    match_rate: float
    matched_tags: list[str]
    missing_tags: list[str]
    extra_tags: list[str]
    image_path: str | None = None
    seed: int | None = None


def build_test_prompt(
    test: TestPrompt,
    character_identity_tags: list[str] | None = None,
    character_clothing_tags: list[str] | None = None,
    lora_trigger_words: list[str] | None = None,
    mode: EvaluationMode = "standard",
) -> str:
    """Build a complete prompt from test definition and character context.

    Args:
        test: Test prompt definition
        character_identity_tags: Character appearance tags (hair, eyes, etc.)
        character_clothing_tags: Character clothing tags
        lora_trigger_words: LoRA trigger words (for mode=lora)
        mode: 'standard' or 'lora'

    Returns:
        Complete prompt string
    """
    from services.prompt import compose_prompt_string

    # Base tokens
    tokens = ["masterpiece", "best quality", test.subject]

    # Add character identity if provided
    if character_identity_tags:
        tokens.extend(character_identity_tags)

    # Add test-specific tokens
    tokens.extend(test.tokens)

    # Add clothing if provided
    if character_clothing_tags:
        tokens.extend(character_clothing_tags)

    # Compose with mode-specific ordering
    return compose_prompt_string(
        tokens=tokens,
        mode=mode,
        trigger_words=lora_trigger_words,
        use_break=(mode == "lora"),
    )


async def run_single_evaluation(
    test_name: str,
    mode: EvaluationMode,
    character_id: int | None,
    db: Session,
    batch_id: str,
    seed: int | None = None,
) -> EvaluationResult | None:
    """Run a single evaluation test.

    Args:
        test_name: Name of the test prompt
        mode: 'standard' or 'lora'
        character_id: Optional character ID for context
        db: Database session
        batch_id: Batch identifier for grouping results
        seed: Optional seed for reproducibility

    Returns:
        EvaluationResult or None if test failed
    """
    import io
    import random

    import httpx
    from PIL import Image

    from config import SD_TIMEOUT_SECONDS, SD_TXT2IMG_URL
    from models import Character, EvaluationRun, LoRA, Tag
    from services.validation import compare_prompt_to_tags, wd14_predict_tags

    test = get_test_prompt(test_name)
    if not test:
        logger.warning("[Eval] Unknown test: %s", test_name)
        return None

    # Resolve character context
    character_name = None
    identity_tags: list[str] = []
    clothing_tags: list[str] = []
    lora_triggers: list[str] = []
    lora_strings: list[str] = []
    negative_prompt = "lowres, bad anatomy, bad hands, text, error"

    if character_id:
        character = db.query(Character).filter(Character.id == character_id).first()
        if character:
            character_name = character.name

            # Resolve identity tags
            if character.identity_tags:
                tags = db.query(Tag).filter(Tag.id.in_(character.identity_tags)).all()
                identity_tags = [t.name for t in tags]

            # Resolve clothing tags
            if character.clothing_tags:
                tags = db.query(Tag).filter(Tag.id.in_(character.clothing_tags)).all()
                clothing_tags = [t.name for t in tags]

            # Resolve LoRAs (for lora mode)
            if mode == "lora" and character.loras:
                lora_ids = [item["lora_id"] for item in character.loras]
                loras = db.query(LoRA).filter(LoRA.id.in_(lora_ids)).all()
                for lora in loras:
                    if lora.trigger_words:
                        lora_triggers.extend(lora.trigger_words)
                    weight = lora.optimal_weight or 0.7
                    lora_strings.append(f"<lora:{lora.name}:{weight}>")

            # Use character's recommended negative + custom negative
            if character.recommended_negative:
                negative_prompt = ", ".join(character.recommended_negative)
            
            if character.custom_negative_prompt:
                negative_prompt = f"{negative_prompt}, {character.custom_negative_prompt}"

    # Build prompt
    prompt = build_test_prompt(
        test=test,
        character_identity_tags=identity_tags,
        character_clothing_tags=clothing_tags,
        lora_trigger_words=lora_triggers if mode == "lora" else None,
        mode=mode,
    )

    # Add custom base prompt if present (already queried 'character' above)
    if character_id and 'character' in locals() and character and character.custom_base_prompt:
        prompt = f"{prompt}, {character.custom_base_prompt}"

    # Add LoRA strings for lora mode
    if mode == "lora" and lora_strings:
        prompt = prompt + ", " + ", ".join(lora_strings)

    # Use random seed if not provided
    if seed is None:
        seed = random.randint(1, 2147483647)

    # Generate image
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": 20,
        "cfg_scale": 7.0,
        "sampler_name": "DPM++ 2M",
        "seed": seed,
        "width": 512,
        "height": 768,
    }

    logger.info("[Eval] Running test=%s mode=%s char=%s", test_name, mode, character_name)

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(SD_TXT2IMG_URL, json=payload, timeout=SD_TIMEOUT_SECONDS)
            res.raise_for_status()
            data = res.json()
            img_b64 = data.get("images", [None])[0]
            if not img_b64:
                logger.error("[Eval] No image returned for %s/%s", test_name, mode)
                return None
    except Exception as e:
        logger.exception("[Eval] Image generation failed: %s", e)
        return None

    # Validate with WD14
    try:
        import base64

        image_bytes = base64.b64decode(img_b64)
        image = Image.open(io.BytesIO(image_bytes))
        tags = wd14_predict_tags(image)
        comparison = compare_prompt_to_tags(prompt, tags)
        total = len(comparison["matched"]) + len(comparison["missing"])
        match_rate = (len(comparison["matched"]) / total) if total else 0.0
    except Exception as e:
        logger.exception("[Eval] WD14 validation failed: %s", e)
        return None

    # Save to database
    run = EvaluationRun(
        test_name=test_name,
        mode=mode,
        character_id=character_id,
        character_name=character_name,
        prompt_used=prompt,
        negative_prompt=negative_prompt,
        match_rate=match_rate,
        matched_tags=comparison["matched"],
        missing_tags=comparison["missing"],
        extra_tags=comparison["extra"],
        seed=seed,
        steps=20,
        cfg_scale=7.0,
        batch_id=batch_id,
    )
    db.add(run)
    db.commit()

    logger.info(
        "[Eval] Result: test=%s mode=%s match_rate=%.2f",
        test_name,
        mode,
        match_rate,
    )

    return EvaluationResult(
        test_name=test_name,
        mode=mode,
        match_rate=match_rate,
        matched_tags=comparison["matched"],
        missing_tags=comparison["missing"],
        extra_tags=comparison["extra"],
        seed=seed,
    )


async def run_evaluation_batch(
    request: EvaluationRequest,
    db: Session,
) -> dict:
    """Run a batch of evaluation tests.

    Args:
        request: Evaluation request with test names and settings
        db: Database session

    Returns:
        Summary of evaluation results
    """
    batch_id = str(uuid.uuid4())[:8]
    modes = request.modes or ["standard", "lora"]
    results: list[EvaluationResult] = []

    for test_name in request.test_names:
        for mode in modes:
            for i in range(request.repetitions):
                result = await run_single_evaluation(
                    test_name=test_name,
                    mode=mode,
                    character_id=request.character_id,
                    db=db,
                    batch_id=batch_id,
                    seed=None,  # Random seed for each run
                )
                if result:
                    results.append(result)

    # Compute summary statistics
    summary = compute_evaluation_summary(results)
    summary["batch_id"] = batch_id
    summary["total_runs"] = len(results)

    return summary


def compute_evaluation_summary(results: list[EvaluationResult]) -> dict:
    """Compute summary statistics from evaluation results.

    Args:
        results: List of evaluation results

    Returns:
        Summary dict with per-test and per-mode statistics
    """
    from collections import defaultdict

    # Group by test and mode
    by_test_mode: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    for r in results:
        by_test_mode[r.test_name][r.mode].append(r.match_rate)

    # Compute averages
    test_summaries = []
    for test_name, modes_data in by_test_mode.items():
        test_summary = {"test_name": test_name}
        for mode, rates in modes_data.items():
            avg_rate = sum(rates) / len(rates) if rates else 0.0
            test_summary[f"{mode}_avg"] = round(avg_rate, 3)
            test_summary[f"{mode}_count"] = len(rates)

        # Compute difference
        std_avg = test_summary.get("standard_avg", 0)
        lora_avg = test_summary.get("lora_avg", 0)
        test_summary["diff"] = round(lora_avg - std_avg, 3)
        test_summary["winner"] = "lora" if lora_avg > std_avg else "standard" if std_avg > lora_avg else "tie"

        test_summaries.append(test_summary)

    # Overall stats
    all_standard = [r.match_rate for r in results if r.mode == "standard"]
    all_lora = [r.match_rate for r in results if r.mode == "lora"]

    overall_standard = sum(all_standard) / len(all_standard) if all_standard else 0.0
    overall_lora = sum(all_lora) / len(all_lora) if all_lora else 0.0

    return {
        "tests": test_summaries,
        "overall": {
            "standard_avg": round(overall_standard, 3),
            "lora_avg": round(overall_lora, 3),
            "diff": round(overall_lora - overall_standard, 3),
            "winner": "lora" if overall_lora > overall_standard else "standard" if overall_standard > overall_lora else "tie",
        },
    }


# ============================================================
# 15.6.4: Query Evaluation Results
# ============================================================


def get_evaluation_results(
    db: Session,
    character_id: int | None = None,
    test_name: str | None = None,
    batch_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Query evaluation results from database.

    Args:
        db: Database session
        character_id: Filter by character
        test_name: Filter by test name
        batch_id: Filter by batch ID
        limit: Max results to return

    Returns:
        List of evaluation run dicts
    """
    from models import EvaluationRun

    query = db.query(EvaluationRun)

    if character_id is not None:
        query = query.filter(EvaluationRun.character_id == character_id)
    if test_name:
        query = query.filter(EvaluationRun.test_name == test_name)
    if batch_id:
        query = query.filter(EvaluationRun.batch_id == batch_id)

    runs = query.order_by(EvaluationRun.created_at.desc()).limit(limit).all()

    return [
        {
            "id": r.id,
            "test_name": r.test_name,
            "mode": r.mode,
            "character_id": r.character_id,
            "character_name": r.character_name,
            "match_rate": r.match_rate,
            "matched_tags": r.matched_tags,
            "missing_tags": r.missing_tags,
            "seed": r.seed,
            "batch_id": r.batch_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in runs
    ]


def get_evaluation_summary(
    db: Session,
    character_id: int | None = None,
) -> dict:
    """Get aggregated evaluation summary for a character.

    Args:
        db: Database session
        character_id: Filter by character (None for all)

    Returns:
        Summary statistics grouped by test and mode
    """
    from sqlalchemy import func

    from models import EvaluationRun

    query = db.query(
        EvaluationRun.test_name,
        EvaluationRun.mode,
        func.avg(EvaluationRun.match_rate).label("avg_rate"),
        func.count(EvaluationRun.id).label("count"),
    )

    if character_id is not None:
        query = query.filter(EvaluationRun.character_id == character_id)

    query = query.group_by(EvaluationRun.test_name, EvaluationRun.mode)
    rows = query.all()

    # Restructure into test-centric format
    from collections import defaultdict

    by_test: dict[str, dict] = defaultdict(lambda: {"test_name": "", "standard_avg": 0, "lora_avg": 0})

    for row in rows:
        test_name, mode, avg_rate, count = row
        by_test[test_name]["test_name"] = test_name
        by_test[test_name][f"{mode}_avg"] = round(float(avg_rate), 3)
        by_test[test_name][f"{mode}_count"] = count

    # Compute diffs and winners
    tests = []
    for data in by_test.values():
        std = data.get("standard_avg", 0)
        lora = data.get("lora_avg", 0)
        data["diff"] = round(lora - std, 3)
        data["winner"] = "lora" if lora > std else "standard" if std > lora else "tie"
        tests.append(data)

    # Overall
    all_std = [t["standard_avg"] for t in tests if "standard_avg" in t]
    all_lora = [t["lora_avg"] for t in tests if "lora_avg" in t]

    overall_std = sum(all_std) / len(all_std) if all_std else 0
    overall_lora = sum(all_lora) / len(all_lora) if all_lora else 0

    return {
        "tests": tests,
        "overall": {
            "standard_avg": round(overall_std, 3),
            "lora_avg": round(overall_lora, 3),
            "diff": round(overall_lora - overall_std, 3),
            "winner": "lora" if overall_lora > overall_std else "standard" if overall_std > overall_lora else "tie",
        },
    }
