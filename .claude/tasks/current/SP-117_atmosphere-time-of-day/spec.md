# SP-117: Atmosphere 에이전트 time_of_day 품질 검증

branch: feat/SP-117_atmosphere-time-of-day
status: running | approved_at: 2026-03-30
priority: P1
scope: backend

## 배경
NoobAI-XL v-pred 모델이 시간 태그 없이 생성 시 dark/night 기본값으로 파란색 이미지를 만드는 문제가 있었음.
PR #358에서 fallback `day` 태그와 Atmosphere 에이전트 `time_of_day` 필드를 추가했지만,
실제 파이프라인에서 Gemini가 대본 맥락에 맞는 시간을 제대로 생성하는지 검증이 필요.

## DoD (Definition of Done)
1. 실제 대본(야근/퇴근/새벽 등)으로 파이프라인 실행 → Gemini가 적절한 `time_of_day` 생성 확인
2. WriterPlan에서 시간 맥락이 Atmosphere 에이전트로 전달되는지 확인
3. Compositor가 `context_tags.time_of_day`를 정확히 병합하는지 확인
4. fallback `day`는 안전망으로만 동작 (Gemini가 time_of_day를 생략했을 때만)

## Scope
- backend (services/agent/nodes/)
