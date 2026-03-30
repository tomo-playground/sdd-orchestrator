# SP-117: Design — Atmosphere time_of_day 품질 검증

## 현황

PR #358에서 time_of_day 시스템 구현 완료:
- Atmosphere 에이전트: Gemini가 WriterPlan 참조하여 time_of_day 생성
- Finalize: 유효값 검증 + fallback "day"
- Composition: 3개 compose 경로에 `_inject_default_time_if_needed()` 통일
- SSOT: `patterns.py` 15개 유효값, `config.py` DEFAULT_TIME_OF_DAY_TAG

검증되지 않은 것: **실제 대본에서 Gemini가 맥락에 맞는 time_of_day를 생성하는가?**

## 검증 전략

### 1. 단위 테스트 — Finalize 검증 로직 (자동화)

`tests/test_finalize_time_of_day.py`:

| 케이스 | 입력 | 기대 출력 |
|--------|------|----------|
| 유효값 통과 | `"night"` | `"night"` |
| list 정규화 | `["sunset"]` | `"sunset"` |
| 빈 list fallback | `[]` | `"day"` |
| 비표준값 fallback | `"afternoon_light"` | `"day"` |
| 공백→언더바 | `"golden hour"` | `"golden_hour"` |
| 가중치 태그 | `"(night:1.1)"` | 통과 (dedup_key 매칭) |

### 2. 단위 테스트 — Composition 기본값 주입 (자동화)

`tests/test_composition_time_of_day.py`:

| 케이스 | 환경 레이어 | 기대 |
|--------|------------|------|
| time 태그 없음 | `["indoor", "office"]` | `"day"` 주입 |
| time 태그 있음 | `["indoor", "night"]` | 주입 안 함 |
| 가중치 time 태그 | `["(sunset:1.2)"]` | 주입 안 함 |

### 3. 통합 테스트 — Atmosphere 에이전트 출력 검증 (Gemini mock)

`tests/test_atmosphere_time_of_day.py`:

Gemini 응답을 mock하여 파싱 로직 검증:
- time_of_day 필드가 있는 정상 응답 → 정상 전달
- time_of_day 필드 누락 → fallback 경로 작동
- 비표준 값 → Finalize에서 정규화

### 4. 수동 검증 — 실제 Gemini 호출 (1회)

시나리오별 대본으로 파이프라인 실행:

| 대본 | 기대 time_of_day |
|------|-----------------|
| "야근 끝나고 퇴근하는 직장인" | night/evening |
| "아침 출근길 커피" | morning |
| "노을 진 해변에서" | sunset/golden_hour |
| "시간 언급 없는 일상" | day (default) |

로그에서 Atmosphere 에이전트 출력의 time_of_day 확인.

## 변경 파일

| 파일 | 변경 | 크기 |
|------|------|------|
| `tests/test_finalize_time_of_day.py` | 신규 — Finalize 검증 테스트 | S |
| `tests/test_composition_time_of_day.py` | 신규 — Composition 기본값 테스트 | S |
| `tests/test_atmosphere_time_of_day.py` | 신규 — Atmosphere 파싱 테스트 | S |

기존 코드 변경 없음. 테스트 추가만.
