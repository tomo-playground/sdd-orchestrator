"""Evaluation API endpoints for Mode A/B quality comparison."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from services.evaluation import (
    TEST_PROMPTS,
    get_evaluation_results,
    get_evaluation_summary,
    get_test_prompts,
    run_evaluation_batch,
    EvaluationRequest,
)

router = APIRouter(prefix="/eval", tags=["evaluation"])


# ============================================================
# Schemas
# ============================================================


class TestPromptInfo(BaseModel):
    """Test prompt information."""

    name: str
    description: str
    tokens: list[str]
    subject: str


class EvaluationRunRequest(BaseModel):
    """Request body for running evaluation."""

    test_names: list[str] = Field(..., description="List of test names to run")
    character_id: int | None = Field(None, description="Character ID for context")
    modes: list[str] | None = Field(
        None, description="Modes to test: ['standard', 'lora']"
    )
    repetitions: int = Field(3, ge=1, le=10, description="Repetitions per test")


class EvaluationRunResponse(BaseModel):
    """Response from evaluation run."""

    batch_id: str
    total_runs: int
    tests: list[dict]
    overall: dict


class EvaluationResultItem(BaseModel):
    """Single evaluation result."""

    id: int
    test_name: str
    mode: str
    character_id: int | None
    character_name: str | None
    match_rate: float | None
    matched_tags: list[str] | None
    missing_tags: list[str] | None
    seed: int | None
    batch_id: str | None
    created_at: str | None


class EvaluationSummaryResponse(BaseModel):
    """Aggregated evaluation summary."""

    tests: list[dict]
    overall: dict


# ============================================================
# Endpoints
# ============================================================


@router.get("/tests", response_model=list[TestPromptInfo])
async def list_test_prompts():
    """List all available test prompts."""
    prompts = get_test_prompts()
    return [
        TestPromptInfo(
            name=p.name,
            description=p.description,
            tokens=p.tokens,
            subject=p.subject,
        )
        for p in prompts.values()
    ]


@router.post("/run", response_model=EvaluationRunResponse)
async def run_evaluation(request: EvaluationRunRequest, db: Session = Depends(get_db)):
    """Run evaluation tests for Mode A/B comparison.

    Generates images with both Standard and LoRA modes,
    validates with WD14, and stores results.
    """
    # Validate test names
    valid_tests = set(TEST_PROMPTS.keys())
    invalid_tests = set(request.test_names) - valid_tests
    if invalid_tests:
        logger.warning("[Eval] Invalid test names: %s", invalid_tests)

    test_names = [t for t in request.test_names if t in valid_tests]
    if not test_names:
        return EvaluationRunResponse(
            batch_id="",
            total_runs=0,
            tests=[],
            overall={"standard_avg": 0, "lora_avg": 0, "diff": 0, "winner": "tie"},
        )

    # Build evaluation request
    eval_request = EvaluationRequest(
        test_names=test_names,
        character_id=request.character_id,
        modes=request.modes,  # type: ignore
        repetitions=request.repetitions,
    )

    logger.info(
        "[Eval] Starting batch: tests=%s, char=%s, modes=%s, reps=%d",
        test_names,
        request.character_id,
        request.modes,
        request.repetitions,
    )

    result = await run_evaluation_batch(eval_request, db)

    return EvaluationRunResponse(
        batch_id=result.get("batch_id", ""),
        total_runs=result.get("total_runs", 0),
        tests=result.get("tests", []),
        overall=result.get("overall", {}),
    )


@router.get("/results", response_model=list[EvaluationResultItem])
async def get_results(
    character_id: int | None = Query(None, description="Filter by character ID"),
    test_name: str | None = Query(None, description="Filter by test name"),
    batch_id: str | None = Query(None, description="Filter by batch ID"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    db: Session = Depends(get_db),
):
    """Get evaluation results with optional filters."""
    results = get_evaluation_results(
        db=db,
        character_id=character_id,
        test_name=test_name,
        batch_id=batch_id,
        limit=limit,
    )
    logger.info("[Eval] Returned %d results", len(results))
    return results


@router.get("/summary", response_model=EvaluationSummaryResponse)
async def get_summary(
    character_id: int | None = Query(None, description="Filter by character ID"),
    db: Session = Depends(get_db),
):
    """Get aggregated evaluation summary.

    Returns average match rates per test and mode,
    with overall comparison statistics.
    """
    summary = get_evaluation_summary(db, character_id=character_id)
    logger.info("[Eval] Summary: %s", summary.get("overall"))
    return EvaluationSummaryResponse(
        tests=summary.get("tests", []),
        overall=summary.get("overall", {}),
    )
