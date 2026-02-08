"""Pydantic schemas for the Lab module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LabExperimentRunRequest(BaseModel):
    """
    Request to run a single experiment.

    Phase 1: Requires group_id for V3 Prompt Engine + Style Profile.
    """

    experiment_type: str = "tag_render"
    group_id: int  # Required: Lab experiments belong to Groups
    character_id: int | None = None
    target_tags: list[str]
    negative_prompt: str | None = None
    sd_params: dict | None = None  # {steps, cfg_scale, sampler, width, height}
    seed: int | None = None
    notes: str | None = None
    scene_description: str | None = None  # for scene_translate type


class LabExperimentResponse(BaseModel):
    """
    Single experiment result.

    Phase 1: Includes V3 metadata (final_prompt, loras_applied).
    """

    id: int
    batch_id: str | None = None
    experiment_type: str
    status: str
    group_id: int
    character_id: int | None = None
    prompt_used: str  # Original tags joined
    negative_prompt: str | None = None
    target_tags: list[str]
    sd_params: dict | None = None
    image_url: str | None = None  # resolved from media_asset_id
    seed: int | None = None
    match_rate: float | None = None
    wd14_result: dict | None = None
    scene_description: str | None = None
    notes: str | None = None
    created_at: datetime | None = None

    # V3 Prompt Engine metadata (Phase 1)
    final_prompt: str | None = None  # Full prompt after V3 composition
    loras_applied: list[dict] | None = None  # [{name, weight, source}]

    model_config = ConfigDict(from_attributes=True)


class LabBatchRunRequest(BaseModel):
    """
    Request to run a batch of experiments.

    Phase 1: Requires group_id for V3 Prompt Engine + Style Profile.
    """

    experiment_type: str = "tag_render"
    group_id: int  # Required: Lab experiments belong to Groups
    character_id: int | None = None
    target_tags: list[str]
    negative_prompt: str | None = None
    sd_params: dict | None = None
    seeds: list[int] | None = None  # specific seeds, or None for random
    count: int = 5  # number of experiments
    notes: str | None = None


class LabBatchRunResponse(BaseModel):
    """Batch experiment result."""

    batch_id: str
    total: int
    completed: int
    failed: int
    experiments: list[LabExperimentResponse]


class TagEffectivenessItem(BaseModel):
    """Single tag effectiveness entry."""

    tag_name: str
    tag_id: int
    use_count: int
    match_count: int
    effectiveness: float


class TagEffectivenessReport(BaseModel):
    """Tag effectiveness aggregated report."""

    items: list[TagEffectivenessItem]
    total_experiments: int
    avg_match_rate: float | None = None


class LabExperimentListResponse(BaseModel):
    """Paginated list of experiments."""

    items: list[LabExperimentResponse]
    total: int
