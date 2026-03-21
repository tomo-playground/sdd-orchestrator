---
id: SP-031
priority: P1
scope: backend
branch: feat/SP-031-gemini-tool-hallucination
created: 2026-03-21
status: pending
depends_on:
label: bug
assignee: stopper2008
---

## 무엇을
Gemini Function Calling 할루시네이션 방어 — 미등록 도구 호출 시 안전 처리

## 왜
Sentry에서 발견된 4개 이슈:
1. Tool 'unknown_tool' not found in executors
2. Tool 'Talking_tool' Failed: ValueError
3. [LangGraph] Writer 노드 실패: Gemini API 실패
4. [LangGraph] Writer 재시도 실패 후 안전 폴백 치환

Gemini가 존재하지 않는 도구를 할루시네이션으로 호출하여 파이프라인 실패 발생.

## 수정 계획
1. Function Calling executor에 unknown tool fallback 추가
2. Tool 이름 validation — 등록된 도구 목록과 대조
3. 할루시네이션 도구 호출 시 무시 + 로그 경고 (파이프라인 중단 방지)
4. Gemini system prompt에 사용 가능 도구 목록 명시 강화

## 관련 파일
- `backend/services/agent/tools/` — Function Calling 도구 정의
- `backend/services/agent/nodes/cinematographer.py` — Tool Calling 사용 노드
- `backend/services/agent/llm_models.py` — Gemini 설정

## 완료 기준 (DoD)
- [ ] 미등록 도구 호출 시 파이프라인 미중단 (graceful skip)
- [ ] Sentry에 경고 이벤트 기록
- [ ] 기존 도구 정상 동작
- [ ] 기존 테스트 통과
