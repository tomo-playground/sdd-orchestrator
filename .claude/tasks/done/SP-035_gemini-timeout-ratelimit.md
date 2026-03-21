---
id: SP-035
priority: P0
scope: backend
branch: feat/SP-035-gemini-timeout-ratelimit
created: 2026-03-21
status: done
depends_on:
label: bug
assignee: stopper2008
---

## 무엇을
Gemini API timeout + rate limit + 동시 호출 제한 — 파이프라인 hang 근본 해결

## 왜
- Gemini 호출에 timeout 없음 → Critic 토론에서 7분+ hang 발생 (2026-03-21 실제 장애)
- generate_parallel에 Semaphore 없음 → 동시 6개 호출 → RPM 초과
- retry delay가 1s/3s → 429 연속 실패

## 수정 범위
1. `gemini_provider.py`: HttpOptions(timeout=120_000) 글로벌 설정
2. `creative_agents.py`: generate_parallel에 Semaphore(5) 추가
3. `gemini_provider.py`: retry delay 지수 백오프 [2, 8, 30]초
4. `config.py`: GEMINI_TIMEOUT_MS, GEMINI_MAX_CONCURRENT 상수 추가

## 완료 기준 (DoD)
- [ ] Gemini 호출에 120초 timeout 적용
- [ ] 동시 호출 5개 제한 (Semaphore)
- [ ] retry delay 지수 백오프
- [ ] 기존 테스트 통과
- [ ] Critic 토론 hang 재현 불가
