"""
벤치마크 실행 엔진 테스트.

run_benchmark.py의 핵심 기능 검증:
- 샘플별 N회 반복 실행
- LangFuse 트레이스 기록
- 결과 저장 (JSON)
- 에러 핸들링
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.benchmark.compare_results import (  # noqa: E402
    compare_narrative_scores,
    validate_gate,
)
from scripts.benchmark.run_benchmark import BenchmarkRunner, run_single_sample  # noqa: E402


class TestBenchmarkRunner:
    """벤치마크 러너 테스트."""

    async def test_run_single_sample_success(self):
        """단일 샘플 실행 성공 케이스."""
        sample = {
            "id": "BM-01",
            "topic": "테스트 주제",
            "structure": "monologue",
            "language": "korean",
            "duration": 30,
            "preset": "full_auto",
            "target": "Phase A",
        }

        # Mock API 호출
        with patch("scripts.benchmark.run_benchmark.call_generate_api") as mock_api:
            mock_api.return_value = {
                "scenes": [{"text": "씬1"}],
                "narrative_score": {"total": 0.75},
                "elapsed_time": 45.2,
            }

            result = await run_single_sample(sample, run_number=1)

            assert result["sample_id"] == "BM-01"
            assert result["run_number"] == 1
            assert "narrative_score" in result
            assert "elapsed_time" in result
            assert result["status"] == "success"

    async def test_run_single_sample_with_langfuse_tag(self):
        """LangFuse 트레이스에 'baseline' 태그가 포함되어야 함."""
        sample = {
            "id": "BM-01",
            "topic": "테스트",
            "structure": "monologue",
            "language": "korean",
            "duration": 30,
            "preset": "full_auto",
        }

        with patch("scripts.benchmark.run_benchmark.call_generate_api") as mock_api:
            mock_api.return_value = {"scenes": [], "elapsed_time": 30}

            await run_single_sample(sample, run_number=1, langfuse_tags=["baseline"])

            # API 호출 시 metadata에 tags 포함 확인
            call_args = mock_api.call_args
            assert "baseline" in call_args.kwargs.get("langfuse_tags", [])

    async def test_run_benchmark_batch(self):
        """여러 샘플을 배치로 실행."""
        samples = [
            {
                "id": "BM-01",
                "topic": "주제1",
                "structure": "monologue",
                "language": "korean",
                "duration": 30,
                "preset": "full_auto",
            },
            {
                "id": "BM-02",
                "topic": "주제2",
                "structure": "dialogue",
                "language": "english",
                "duration": 30,
                "preset": "creator",
            },
        ]

        with patch("scripts.benchmark.run_benchmark.run_single_sample") as mock_run:
            mock_run.return_value = {
                "sample_id": "BM-01",
                "status": "success",
                "elapsed_time": 45.0,
                "narrative_score": {"total": 0.75},
            }

            runner = BenchmarkRunner(samples, runs_per_sample=2)
            results = await runner.run_all()

            # 2개 샘플 × 2회 = 4번 실행
            assert mock_run.call_count == 4
            assert len(results) == 4

    async def test_benchmark_error_handling(self):
        """샘플 실행 실패 시 에러를 기록하고 계속 진행."""
        sample = {
            "id": "BM-01",
            "topic": "주제",
            "structure": "monologue",
            "language": "korean",
            "duration": 30,
            "preset": "full_auto",
        }

        with patch("scripts.benchmark.run_benchmark.call_generate_api") as mock_api:
            mock_api.side_effect = Exception("API Error")

            result = await run_single_sample(sample, run_number=1)

            assert result["status"] == "error"
            assert "API Error" in result["error_message"]

    def test_save_results_to_json(self, tmp_path):
        """결과를 JSON 파일로 저장."""
        results = [
            {"sample_id": "BM-01", "run_number": 1, "narrative_score": {"total": 0.8}},
            {"sample_id": "BM-01", "run_number": 2, "narrative_score": {"total": 0.75}},
        ]

        output_file = tmp_path / "baseline_results.json"

        runner = BenchmarkRunner([], runs_per_sample=2)
        runner.save_results(results, output_file)

        assert output_file.exists()

        with open(output_file) as f:
            saved = json.load(f)

        assert len(saved["results"]) == 2
        assert saved["metadata"]["total_runs"] == 2


class TestBenchmarkComparison:
    """벤치마크 비교 분석 테스트."""

    def test_compare_narrative_scores(self):
        """Baseline vs Phase X의 NarrativeScore 평균 비교."""
        baseline = [
            {"sample_id": "BM-01", "status": "success", "narrative_score": {"total": 0.65}},
            {"sample_id": "BM-01", "status": "success", "narrative_score": {"total": 0.70}},
        ]
        phase_a = [
            {"sample_id": "BM-01", "status": "success", "narrative_score": {"total": 0.75}},
            {"sample_id": "BM-01", "status": "success", "narrative_score": {"total": 0.80}},
        ]

        improvement = compare_narrative_scores(baseline, phase_a)

        # (0.775 - 0.675) / 0.675 ≈ 14.8%
        assert improvement["percent_change"] > 10
        assert improvement["baseline_avg"] == pytest.approx(0.675)
        assert improvement["phase_avg"] == pytest.approx(0.775)

    def test_gate_validation_pass(self):
        """Gate 조건 충족 검증 (Phase A: +10% 이상)."""
        baseline_avg = 0.65
        phase_a_avg = 0.72  # +10.8%

        result = validate_gate(baseline_avg=baseline_avg, phase_avg=phase_a_avg, threshold_percent=10)

        assert result["passed"] is True
        assert result["improvement_percent"] > 10

    def test_gate_validation_fail(self):
        """Gate 조건 미충족 검증."""
        baseline_avg = 0.65
        phase_a_avg = 0.68  # +4.6%만 향상 (10% 미달)

        result = validate_gate(baseline_avg=baseline_avg, phase_avg=phase_a_avg, threshold_percent=10)

        assert result["passed"] is False
        assert result["improvement_percent"] < 10
