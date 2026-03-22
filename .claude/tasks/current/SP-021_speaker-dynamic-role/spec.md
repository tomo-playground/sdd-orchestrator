---
id: SP-021
priority: P1
scope: fullstack
branch: feat/SP-021-speaker-dynamic-role
created: 2026-03-21
status: pending
depends_on: SP-020, SP-056
label: enhancement
assignee: stopper2008
---

## 무엇을
정적 A/B/Narrator → speaker_1/speaker_2/narrator 동적 역할 전환 (Phase A)

## 왜
- 현재 speaker가 `"A"`, `"B"`, `"Narrator"` 3개 하드코딩
- 3인 이상 대화 구조 확장 불가
- UI에서 캐릭터명 대신 "A", "B" 표시 — 사용성 저하

## 완료 기준 (DoD)
- [ ] `config.py`의 `SPEAKER_A/B` → `speaker_1/speaker_2` 전환
- [ ] `_VALID_SPEAKERS` 맵 동적 생성 (structure 기반)
- [ ] DB `scenes.speaker` 컬럼 마이그레이션 (`"A"` → `"speaker_1"`)
- [ ] Frontend SpeakerBadge 동적 렌더링 (캐릭터명 표시)
- [ ] Gemini 프롬프트 템플릿의 speaker 예시 업데이트
- [ ] 기존 기능 regression 없음

## 제약
- 변경 파일 10개 이하 목표
- 건드리면 안 되는 것: TTS 엔진 로직 (speaker 매핑만 변경)
- DB 마이그레이션 포함 → DBA 리뷰 필수
- Enum ID 정규화(SP-020) 선행 권장

## 힌트
- 명세: `docs/01_product/FEATURES/SPEAKER_DYNAMIC_ROLE.md`
- 관련 파일: `backend/config.py`, `backend/services/agent/nodes/creative_qc.py`, `frontend/app/components/scene/SpeakerBadge.tsx`
