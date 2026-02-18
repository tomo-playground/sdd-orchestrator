#!/usr/bin/env python3
"""
벤치마크 결과 비교 분석 스크립트.

사용법:
    python compare_results.py baseline_results.json phase_a_results.json --threshold 10
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_results(file_path: Path) -> list[dict[str, Any]]:
    """결과 파일 로드."""
    with open(file_path) as f:
        data = json.load(f)
    return data["results"]


def compare_narrative_scores(
    baseline: list[dict[str, Any]],
    phase: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    NarrativeScore 평균 비교.

    Returns:
        {
            "baseline_avg": 0.675,
            "phase_avg": 0.775,
            "percent_change": 14.8,
            "absolute_change": 0.10
        }
    """
    # Success 결과만 필터
    baseline_scores = [
        r["narrative_score"]["total"]
        for r in baseline
        if r["status"] == "success" and r.get("narrative_score")
    ]
    phase_scores = [
        r["narrative_score"]["total"]
        for r in phase
        if r["status"] == "success" and r.get("narrative_score")
    ]

    if not baseline_scores or not phase_scores:
        raise ValueError("No valid scores to compare")

    baseline_avg = sum(baseline_scores) / len(baseline_scores)
    phase_avg = sum(phase_scores) / len(phase_scores)

    absolute_change = phase_avg - baseline_avg
    percent_change = (absolute_change / baseline_avg) * 100

    return {
        "baseline_avg": baseline_avg,
        "phase_avg": phase_avg,
        "absolute_change": absolute_change,
        "percent_change": percent_change,
    }


def validate_gate(
    baseline_avg: float,
    phase_avg: float,
    threshold_percent: float,
) -> dict[str, Any]:
    """
    Gate 조건 검증.

    Args:
        baseline_avg: Baseline 평균 점수
        phase_avg: Phase 평균 점수
        threshold_percent: 최소 요구 개선율 (예: 10.0 = 10%)

    Returns:
        {
            "passed": True/False,
            "improvement_percent": 14.8,
            "threshold_percent": 10.0
        }
    """
    improvement = ((phase_avg - baseline_avg) / baseline_avg) * 100
    passed = improvement >= threshold_percent

    return {
        "passed": passed,
        "improvement_percent": improvement,
        "threshold_percent": threshold_percent,
    }


def print_comparison_report(
    baseline_file: Path,
    phase_file: Path,
    threshold: float,
) -> None:
    """비교 리포트 출력."""
    baseline = load_results(baseline_file)
    phase = load_results(phase_file)

    print(f"\n{'=' * 70}")
    print(f"Benchmark Comparison Report")
    print(f"{'=' * 70}")
    print(f"Baseline: {baseline_file.name}")
    print(f"Phase:    {phase_file.name}")
    print(f"Gate Threshold: +{threshold}%")
    print(f"{'=' * 70}\n")

    # NarrativeScore 비교
    try:
        score_comparison = compare_narrative_scores(baseline, phase)

        print("NarrativeScore Comparison:")
        print(f"  Baseline Avg:  {score_comparison['baseline_avg']:.4f}")
        print(f"  Phase Avg:     {score_comparison['phase_avg']:.4f}")
        print(f"  Absolute Δ:    {score_comparison['absolute_change']:+.4f}")
        print(f"  Percent Δ:     {score_comparison['percent_change']:+.2f}%")

        # Gate 검증
        gate_result = validate_gate(
            score_comparison["baseline_avg"],
            score_comparison["phase_avg"],
            threshold,
        )

        print(f"\nGate Validation:")
        print(f"  Required: +{gate_result['threshold_percent']:.1f}%")
        print(f"  Actual:   {gate_result['improvement_percent']:+.2f}%")

        if gate_result["passed"]:
            print(f"  Result:   ✓ PASS")
        else:
            print(f"  Result:   ✗ FAIL")

    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # 샘플별 상세 분석
    print(f"\n{'=' * 70}")
    print("Per-Sample Analysis:")
    print(f"{'=' * 70}")

    # 샘플별 그룹화
    baseline_by_sample = {}
    phase_by_sample = {}

    for r in baseline:
        if r["status"] == "success" and r.get("narrative_score"):
            sample_id = r["sample_id"]
            if sample_id not in baseline_by_sample:
                baseline_by_sample[sample_id] = []
            baseline_by_sample[sample_id].append(r["narrative_score"]["total"])

    for r in phase:
        if r["status"] == "success" and r.get("narrative_score"):
            sample_id = r["sample_id"]
            if sample_id not in phase_by_sample:
                phase_by_sample[sample_id] = []
            phase_by_sample[sample_id].append(r["narrative_score"]["total"])

    for sample_id in sorted(baseline_by_sample.keys()):
        b_scores = baseline_by_sample.get(sample_id, [])
        p_scores = phase_by_sample.get(sample_id, [])

        if not b_scores or not p_scores:
            continue

        b_avg = sum(b_scores) / len(b_scores)
        p_avg = sum(p_scores) / len(p_scores)
        delta = ((p_avg - b_avg) / b_avg) * 100

        symbol = "✓" if delta > 0 else "✗"
        print(f"  {sample_id}: {b_avg:.3f} → {p_avg:.3f} ({delta:+.1f}%) {symbol}")

    print(f"\n{'=' * 70}")


def main():
    """메인 실행."""
    parser = argparse.ArgumentParser(description="Compare benchmark results")
    parser.add_argument("baseline", type=Path, help="Baseline results file")
    parser.add_argument("phase", type=Path, help="Phase results file")
    parser.add_argument(
        "--threshold",
        type=float,
        default=10.0,
        help="Gate threshold percent (default: 10.0)",
    )

    args = parser.parse_args()

    if not args.baseline.exists():
        print(f"ERROR: Baseline file not found: {args.baseline}")
        sys.exit(1)

    if not args.phase.exists():
        print(f"ERROR: Phase file not found: {args.phase}")
        sys.exit(1)

    print_comparison_report(args.baseline, args.phase, args.threshold)


if __name__ == "__main__":
    main()
