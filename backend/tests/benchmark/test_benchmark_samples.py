"""
벤치마크 샘플 데이터 검증 테스트.

BM-01~10 샘플이 명세를 만족하는지 검증:
- 모든 필수 필드 존재
- 난이도/구조/언어 분포 요구사항 충족
- ID 중복 없음
"""

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SAMPLES_PATH = PROJECT_ROOT / "scripts" / "benchmark" / "benchmark_samples.json"


@pytest.fixture
def samples():
    """벤치마크 샘플 로드."""
    if not SAMPLES_PATH.exists():
        pytest.skip(f"Samples file not found: {SAMPLES_PATH}")

    with open(SAMPLES_PATH) as f:
        data = json.load(f)
    return data["samples"]


def test_samples_file_exists():
    """샘플 파일이 존재해야 함."""
    assert SAMPLES_PATH.exists(), f"Missing: {SAMPLES_PATH}"


def test_samples_count(samples):
    """샘플이 정확히 10개여야 함."""
    assert len(samples) == 10, f"Expected 10 samples, got {len(samples)}"


def test_sample_ids_unique(samples):
    """샘플 ID가 중복 없이 BM-01~10이어야 함."""
    ids = [s["id"] for s in samples]
    assert len(ids) == len(set(ids)), "Duplicate IDs found"

    expected_ids = [f"BM-{i:02d}" for i in range(1, 11)]
    assert sorted(ids) == sorted(expected_ids), f"Expected {expected_ids}, got {ids}"


def test_sample_required_fields(samples):
    """모든 샘플에 필수 필드가 존재해야 함."""
    required = ["id", "topic", "structure", "language", "duration", "preset", "target"]

    for sample in samples:
        for field in required:
            assert field in sample, f"Sample {sample.get('id')} missing field: {field}"


def test_sample_structure_distribution(samples):
    """구조 분포: Monologue 4건, Dialogue 3건, Narrated Dialogue 3건."""
    structures = [s["structure"] for s in samples]

    assert structures.count("monologue") == 4, "Expected 4 monologue samples"
    assert structures.count("dialogue") == 3, "Expected 3 dialogue samples"
    assert structures.count("narrated_dialogue") == 3, "Expected 3 narrated_dialogue samples"


def test_sample_language_distribution(samples):
    """언어 분포: Korean 6건, English 2건, Japanese 2건."""
    languages = [s["language"] for s in samples]

    assert languages.count("korean") == 6, "Expected 6 korean samples"
    assert languages.count("english") == 2, "Expected 2 english samples"
    assert languages.count("japanese") == 2, "Expected 2 japanese samples"


def test_sample_valid_duration(samples):
    """Duration이 유효한 값이어야 함 (30 또는 45)."""
    for sample in samples:
        duration = sample["duration"]
        assert duration in [30, 45], f"Invalid duration {duration} in {sample['id']}"


def test_sample_valid_preset(samples):
    """Preset이 유효한 값이어야 함."""
    valid_presets = ["full_auto", "creator"]

    for sample in samples:
        preset = sample["preset"]
        assert preset in valid_presets, f"Invalid preset {preset} in {sample['id']}"


def test_sample_target_phase_coverage(samples):
    """각 Phase가 최소 1개 이상의 타겟 샘플을 가져야 함."""
    targets = " ".join(s["target"] for s in samples)

    # Phase A 검증 항목들
    assert "Phase A" in targets, "No samples targeting Phase A"
    assert "Planning" in targets, "No samples targeting Writer Planning"
    assert "Reflection" in targets, "No samples targeting Review Reflection"
    assert "ReAct" in targets, "No samples targeting Director ReAct"

    # Phase B 검증 항목들
    assert "Phase B" in targets, "No samples targeting Phase B"
    assert "Tool-Calling" in targets or "Research" in targets, "No samples targeting Tool-Calling"

    # Phase C 검증 항목들
    assert "Phase C" in targets, "No samples targeting Phase C"
    assert "토론" in targets or "Communication" in targets, "No samples targeting Agent Communication"


def test_sample_references_field_optional(samples):
    """References 필드는 선택적이며, 있으면 리스트여야 함."""
    for sample in samples:
        if "references" in sample:
            assert isinstance(sample["references"], list), f"Sample {sample['id']} references must be a list"
            assert len(sample["references"]) > 0, f"Sample {sample['id']} references should not be empty"
