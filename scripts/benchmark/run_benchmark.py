#!/usr/bin/env python3
"""
벤치마크 실행 스크립트.

사용법:
    python run_benchmark.py --phase baseline --runs 10
    python run_benchmark.py --phase phase_a --runs 10
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

# timezone.utc를 UTC로 별칭 (Python 3.11+ 호환)
UTC = UTC

# 프로젝트 루트를 Python path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

# Backend config에서 API URL 가져오기
try:
    from config import API_PUBLIC_URL  # noqa: E402
except ImportError:
    # Fallback to environment variable
    import os

    API_PUBLIC_URL = os.getenv("API_PUBLIC_URL", "http://localhost:8000")

SAMPLES_PATH = Path(__file__).parent / "benchmark_samples.json"
RESULTS_DIR = Path(__file__).parent / "results"


def load_samples() -> list[dict[str, Any]]:
    """벤치마크 샘플 로드."""
    with open(SAMPLES_PATH) as f:
        data = json.load(f)
    return data["samples"]


async def call_generate_api(
    sample: dict[str, Any],
    langfuse_tags: list[str] | None = None,
) -> dict[str, Any]:
    """
    Backend /scripts/generate API 호출.

    Returns:
        {
            "scenes": [...],
            "narrative_score": {"total": 0.75, ...},
            "elapsed_time": 45.2,
            "trace_id": "abc123..."
        }
    """
    payload = {
        "topic": sample["topic"],
        "description": sample.get("description", ""),
        "structure": sample["structure"],
        "language": sample["language"],
        "duration": sample["duration"],
        "preset": sample["preset"],
        "references": sample.get("references", []),
    }

    # LangFuse 태그 추가
    if langfuse_tags:
        payload["langfuse_tags"] = langfuse_tags

    async with httpx.AsyncClient(timeout=300.0) as client:
        # SSE 스트림 소비
        async with client.stream(
            "POST",
            f"{API_PUBLIC_URL}/scripts/generate",
            json=payload,
        ) as response:
            response.raise_for_status()

            # SSE 이벤트 파싱 - 스크립트 생성 결과를 포함한 마지막 이벤트 사용
            final_result = None
            async for line in response.aiter_lines():
                if not line.strip():
                    continue  # 빈 줄 스킵

                # SSE 형식: "data: {...}" 또는 바로 JSON
                line_data = line[6:] if line.startswith("data: ") else line

                try:
                    data = json.loads(line_data)
                except json.JSONDecodeError:
                    continue  # 잘못된 JSON은 스킵

                # scenes가 있는 데이터를 최종 결과로 저장
                if "scenes" in data:
                    final_result = data

            if final_result is None:
                raise RuntimeError("No script result received from SSE stream")

            return final_result


async def run_single_sample(
    sample: dict[str, Any],
    run_number: int,
    langfuse_tags: list[str] | None = None,
) -> dict[str, Any]:
    """
    단일 샘플 1회 실행.

    Returns:
        {
            "sample_id": "BM-01",
            "run_number": 1,
            "status": "success" | "error",
            "narrative_score": {...},
            "elapsed_time": 45.2,
            "trace_id": "abc123...",
            "error_message": "..."  # status == "error" 시
        }
    """
    start_time = time.time()

    try:
        result = await call_generate_api(sample, langfuse_tags=langfuse_tags)

        elapsed = time.time() - start_time

        return {
            "sample_id": sample["id"],
            "run_number": run_number,
            "status": "success",
            "narrative_score": result.get("narrative_score"),
            "elapsed_time": elapsed,
            "trace_id": result.get("trace_id"),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        elapsed = time.time() - start_time

        return {
            "sample_id": sample["id"],
            "run_number": run_number,
            "status": "error",
            "error_message": str(e),
            "elapsed_time": elapsed,
            "timestamp": datetime.now(UTC).isoformat(),
        }


class BenchmarkRunner:
    """벤치마크 실행 엔진."""

    def __init__(self, samples: list[dict[str, Any]], runs_per_sample: int = 10):
        self.samples = samples
        self.runs_per_sample = runs_per_sample

    async def run_all(
        self,
        langfuse_tags: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """모든 샘플 × N회 실행."""
        results = []

        for sample in self.samples:
            print(f"\n[{sample['id']}] {sample['topic']}")

            for run_num in range(1, self.runs_per_sample + 1):
                print(f"  Run {run_num}/{self.runs_per_sample}...", end=" ", flush=True)

                result = await run_single_sample(
                    sample,
                    run_number=run_num,
                    langfuse_tags=langfuse_tags,
                )

                if result["status"] == "success":
                    narrative_score = result.get("narrative_score") or {}
                    score = narrative_score.get("total", 0) if narrative_score else 0
                    elapsed = result["elapsed_time"]
                    print(f"✓ Score={score:.2f}, Time={elapsed:.1f}s")
                else:
                    print(f"✗ Error: {result['error_message'][:50]}")

                results.append(result)

        return results

    def save_results(self, results: list[dict[str, Any]], output_file: Path) -> None:
        """결과를 JSON 파일로 저장."""
        output_file.parent.mkdir(parents=True, exist_ok=True)

        metadata = {
            "total_runs": len(results),
            "total_samples": len(self.samples),
            "runs_per_sample": self.runs_per_sample,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        with open(output_file, "w") as f:
            json.dump({"metadata": metadata, "results": results}, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Results saved: {output_file}")


async def main():
    """메인 실행."""
    parser = argparse.ArgumentParser(description="Run benchmark tests")
    parser.add_argument(
        "--phase",
        required=True,
        choices=["baseline", "phase_a", "phase_b", "phase_c"],
        help="Phase to benchmark",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=10,
        help="Runs per sample (default: 10)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path (default: results/{phase}_{timestamp}.json)",
    )

    args = parser.parse_args()

    # 샘플 로드
    samples = load_samples()
    print(f"Loaded {len(samples)} benchmark samples")

    # LangFuse 태그 설정
    langfuse_tags = [args.phase]

    # 러너 생성 및 실행
    runner = BenchmarkRunner(samples, runs_per_sample=args.runs)

    print(f"\nStarting {args.phase} benchmark ({args.runs} runs per sample)...")
    results = await runner.run_all(langfuse_tags=langfuse_tags)

    # 결과 저장
    if args.output:
        output_file = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = RESULTS_DIR / f"{args.phase}_{timestamp}.json"

    runner.save_results(results, output_file)

    # 요약 출력
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = sum(1 for r in results if r["status"] == "error")

    print(f"\n{'=' * 60}")
    print(f"Benchmark Complete: {args.phase}")
    print(f"  Success: {success_count}/{len(results)}")
    print(f"  Errors:  {error_count}/{len(results)}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(main())
