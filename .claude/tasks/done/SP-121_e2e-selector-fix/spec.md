# SP-121: E2E 테스트 셀렉터 수정

- **approved_at**: 2026-03-30
- **branch**: feat/SP-121-e2e-selector-fix
- **priority**: P2
- **scope**: frontend/e2e
- **assignee**: AI
- **created**: 2026-03-30
- **issue**: #364

## 배경

e2e 테스트 모듈 설치 후 전체 실행 결과 19건 중 7건 실패.
Playwright 프레임워크는 정상 — UI 변경 후 테스트 셀렉터가 동기화되지 않은 것이 원인.

## 실패 분류

### A. UI 셀렉터 불일치 (4건)

| 테스트 | 기대 | 실제 |
|--------|------|------|
| `smoke.spec.ts` — Studio page | `?new=true` → "대본" 탭/"영상 목록" | 시리즈 선택 화면 (그룹 버튼 + 토스트) |
| `qa-patrol` — Styles 목록 | `h1, h2` 헤딩 | 리스트-디테일 레이아웃 (`listbox` 사용, h1/h2 없음) |
| `qa-patrol` — Voices 목록 | `h1, h2` 헤딩 | 리스트-디테일 레이아웃 (h1/h2 없음) |
| `qa-patrol` — LoRA redirect | `/library/loras` → `h1, h2` | `/dev/sd-models`로 308 redirect, Admin에 h1/h2 없음 |

### B. 병렬 부하 transient 500 (3건)

| 테스트 | 에러 |
|--------|------|
| `qa-patrol` — 새 영상 | 콘솔에서 500 감지 (`/studio`) |
| `qa-patrol` — Characters 목록 | 콘솔에서 500 감지 (`/library/characters`) |
| `qa-patrol` — Library 메인 | 콘솔에서 500 감지 (`/library/characters`) |

> curl 직접 확인 시 모두 200 정상. 12 worker 병렬 부하에 의한 간헐적 에러.

## DoD (Definition of Done)

- [ ] `qa-patrol.config.ts`: Styles/Voices 셀렉터를 `listbox` 또는 실제 DOM 요소로 변경
- [ ] `qa-patrol.config.ts`: LoRA 셀렉터를 Admin 레이아웃에 맞게 변경
- [ ] `smoke.spec.ts`: Studio `?new=true` 시나리오를 시리즈 선택 화면에 맞게 수정
- [ ] B그룹 transient 500 대응: worker 수 제한 또는 `assertNoCriticalErrors`에서 리소스 로드 에러 필터링
- [ ] `npx playwright test --config=playwright.e2e.config.ts --reporter=list` 전체 PASS

## 수정 대상 파일

- `frontend/e2e/qa-patrol.config.ts`
- `frontend/e2e/smoke.spec.ts`
- `frontend/playwright.e2e.config.ts` (worker 수 제한 시)
