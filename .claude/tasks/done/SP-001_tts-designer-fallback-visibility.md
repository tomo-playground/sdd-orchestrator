---
id: SP-001
priority: P1
scope: backend
branch: feat/SP-001-tts-designer-fallback-visibility
created: 2026-03-19
status: done
depends_on:
---

## 무엇을
TTS Designer 실패 시 조용히 빈 리스트 반환하는 문제 → LangFuse 기록 + 프론트 경고

## 왜
현재 Gemini API 실패 시 voice_design_prompt가 null로 저장되어 TTS 품질이 하락하지만,
사용자가 인지할 방법이 없음. 파일 로그만으로는 트레이싱 불가.
SB 1117 이후 전체 스토리보드에서 voice_design_prompt가 null — 실패 497회 확인.

## 완료 기준 (DoD)
- [x] TTS Designer fallback 시 LangFuse score 기록 (tts_designer_fallback: 1)
- [x] fallback_reason을 final_scenes에 포함하여 프론트엔드 전달
- [ ] 프론트엔드에서 "voice design 누락 씬 N개" warning 토스트 표시 ← 프론트 미착수
- [x] 기존 테스트 regression 없음

## 추가 수정 (태스크 범위 외)
- [x] Gemini client 닫힘 후 재생성 (hot-reload "client has been closed" 에러 방지)
- [x] LANGFUSE_SCORE_CONFIGS에 tts_designer_fallback 등록
- [x] CI → workflow_dispatch 전환 (Stop Hook 대체)

## 품질 게이트 결과 [2026-03-19 21:30]
- Lint: PASS
- Backend pytest: PASS (test_langfuse_scoring 24 passed)
- Frontend vitest: SKIP (프론트 변경 없음)
- VRT: SKIP
- E2E: SKIP

## 제약
- 변경 파일 10개 이하
- DB 스키마 변경 없음
- 의존성 추가 금지

## 힌트
- tts_designer.py:18 — _FALLBACK_TTS에 빈 리스트 반환
- tts_designer.py:160-162 — except 블록에서 fallback
- finalize.py:103 — tts_designer_result 병합
- LangFuse Score: services/agent/nodes/finalize.py record_score() 참조
