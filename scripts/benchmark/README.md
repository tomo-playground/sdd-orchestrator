# Benchmark System

Phase 10 True Agentic Architecture A/B 테스트용 벤치마크 시스템.

## 구조

```
scripts/benchmark/
├── benchmark_samples.json  # BM-01~10 샘플 정의
├── run_benchmark.py        # 벤치마크 실행 스크립트
├── compare_results.py      # 결과 비교 분석 스크립트
├── results/                # 실행 결과 저장 (gitignore)
│   ├── baseline_*.json
│   ├── phase_a_*.json
│   └── ...
└── README.md
```

## 사용법

### 1. Baseline 수집 (Phase 0)

```bash
# Backend 서버 실행 (별도 터미널)
cd backend
uvicorn main:app --reload

# Baseline 벤치마크 실행 (샘플 10개 × 10회 = 100회)
cd scripts/benchmark
python run_benchmark.py --phase baseline --runs 10
```

**결과**: `results/baseline_YYYYMMDD_HHMMSS.json`

### 2. Phase A 실행 (ReAct + Self-Reflection 구현 후)

```bash
# Phase A 구현 완료 후
python run_benchmark.py --phase phase_a --runs 10
```

**결과**: `results/phase_a_YYYYMMDD_HHMMSS.json`

### 3. 결과 비교 (Gate 검증)

```bash
python compare_results.py \
  results/baseline_20260218_120000.json \
  results/phase_a_20260218_140000.json \
  --threshold 10
```

**출력 예시**:
```
======================================================================
Benchmark Comparison Report
======================================================================
Baseline: baseline_20260218_120000.json
Phase:    phase_a_20260218_140000.json
Gate Threshold: +10%
======================================================================

NarrativeScore Comparison:
  Baseline Avg:  0.6750
  Phase Avg:     0.7725
  Absolute Δ:    +0.0975
  Percent Δ:     +14.44%

Gate Validation:
  Required: +10.0%
  Actual:   +14.44%
  Result:   ✓ PASS

======================================================================
Per-Sample Analysis:
======================================================================
  BM-01: 0.680 → 0.750 (+10.3%) ✓
  BM-02: 0.670 → 0.780 (+16.4%) ✓
  BM-03: 0.650 → 0.740 (+13.8%) ✓
  ...
======================================================================
```

### 4. Phase B/C 실행

동일한 방식으로 Phase B, Phase C 실행 및 비교:

```bash
# Phase B
python run_benchmark.py --phase phase_b --runs 10
python compare_results.py baseline.json phase_b.json --threshold 15

# Phase C
python run_benchmark.py --phase phase_c --runs 10
python compare_results.py baseline.json phase_c.json --threshold 20
```

## 샘플 분포

- **총 10개 샘플** (BM-01 ~ BM-10)
- **구조**: Monologue 4건, Dialogue 3건, Narrated Dialogue 3건
- **언어**: Korean 6건, English 2건, Japanese 2건
- **난이도**: Easy 1건, Medium 5건, Hard 4건

## Gate 조건

| Phase | 측정 지표 | 최소 개선율 | 추가 조건 |
|-------|----------|-----------|----------|
| Phase A | NarrativeScore | +10% | 일관성 (분산도 +20% 이내) |
| Phase B | Match Rate (유효 태그 비율) | +15% | - |
| Phase C | NarrativeScore + 레이턴시 | +20% | 120초 이내 |

## LangFuse 트레이스

모든 벤치마크 실행은 LangFuse에 태그되어 기록됩니다:

- `baseline` — Baseline 실행
- `phase_a` — Phase A 실행
- `phase_b` — Phase B 실행
- `phase_c` — Phase C 실행

LangFuse 대시보드에서 Phase별 트레이스를 필터링하여 확인할 수 있습니다.

## 환경 변수

```bash
# .env 또는 export
export API_PUBLIC_URL=http://localhost:8000  # Backend API URL
```

## 테스트

```bash
# 샘플 데이터 검증 테스트
cd backend
pytest tests/benchmark/test_benchmark_samples.py -v

# 러너 테스트 (구현 완료 후 skip 제거)
pytest tests/benchmark/test_benchmark_runner.py -v
```

## 결과 파일 형식

```json
{
  "metadata": {
    "total_runs": 100,
    "total_samples": 10,
    "runs_per_sample": 10,
    "timestamp": "2026-02-18T12:00:00"
  },
  "results": [
    {
      "sample_id": "BM-01",
      "run_number": 1,
      "status": "success",
      "narrative_score": {
        "total": 0.75,
        "hook": 0.8,
        "emotional_arc": 0.7,
        "twist": 0.0,
        "tone_consistency": 0.9,
        "coherence": 0.85
      },
      "elapsed_time": 45.2,
      "trace_id": "abc123...",
      "timestamp": "2026-02-18T12:01:30"
    },
    ...
  ]
}
```

## 참고

- 벤치마크 명세: `docs/01_product/FEATURES/TRUE_AGENTIC_ARCHITECTURE.md` 섹션 11
- Phase 10 로드맵: `docs/01_product/ROADMAP.md` Phase 10
