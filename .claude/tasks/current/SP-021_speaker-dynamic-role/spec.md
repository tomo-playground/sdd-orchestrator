---
id: SP-021
priority: P1
scope: fullstack
branch: feat/SP-021-speaker-dynamic-role
created: 2026-03-21
status: approved
approved_at: 2026-03-23
depends_on: SP-020
label: enhancement
assignee: stopper2008
---

## 무엇을
정적 A/B/Narrator → speaker_1/speaker_2/narrator 동적 역할 전환 (Phase A)

## 왜
- 현재 speaker가 `"A"`, `"B"`, `"Narrator"` 3개 하드코딩
- 3인 이상 대화 구조 확장 불가
- UI에서 캐릭터명 대신 "A", "B" 표시 — 사용성 저하

## 현재 상태 (2026-03-23 코드 감사)

### 이미 완료된 부분
- ORM 모델: `storyboard.character_id`/`character_b_id` 컬럼 **이미 제거됨** → `storyboard_characters` 관계만 사용
- `StoryboardDetailResponse`에 `characters: list[StoryboardCharacterResponse]` 필드 **이미 존재**
- `speaker_resolver.py`, `casting_sync.py` 동적 인프라 완비
- `storyboard_characters` 테이블 + ORM 관계 완전 동작 중
- TTS `tts_helpers.py`에 speaker 파라미터 이미 추가 (동적 처리 가능)

### 아직 미변경 (Phase A 대상)
- `config.py`: `SPEAKER_A = "A"`, `SPEAKER_B = "B"`, `DEFAULT_SPEAKER = "Narrator"` (구 형식)
- `_review_validators.py`: `VALID_SPEAKERS = {"Narrator", "A", "B"}` (하드코딩)
- `creative_qc.py`: `_VALID_SPEAKERS` dict — `"A"`, `"B"` 하드코딩
- Frontend 타입: `speaker: "Narrator" | "A" | "B"` (고정 유니언)
- 테스트 fixture: 37+ 파일에서 구 형식 사용
- API 스키마: `StoryboardSave`에 여전히 `character_id`/`character_b_id` 2필드 (Phase B 범위)

### 혼용 상태 (주의)
- `script_postprocess.py` 등 일부 서비스에서 `"speaker_1"`, `"speaker_2"` 신규 형식 이미 사용
- 나머지 코드는 구 형식 → **형식 불일치 리스크**

## 완료 기준 (DoD) — Phase A만

### Speaker ID 정규화
- [ ] `config.py`의 `SPEAKER_A/B` → `speaker_1/speaker_2`, `DEFAULT_SPEAKER` → `narrator`
- [ ] `_review_validators.py` `VALID_SPEAKERS` → 신규 ID 세트
- [ ] `creative_qc.py` `_VALID_SPEAKERS` → structure별 신규 ID
- [ ] DB `scenes.speaker` 데이터 마이그레이션 (`"A"` → `"speaker_1"`, `"B"` → `"speaker_2"`, `"Narrator"` → `"narrator"`)

### 코드 전수 업데이트
- [ ] Backend 서비스에서 구 형식 (`"A"`, `"B"`, `"Narrator"`) 문자열 비교 0건
- [ ] `script_postprocess.py` 등 이미 신규 형식 사용 중인 코드와 통일
- [ ] Gemini 프롬프트 템플릿의 speaker 예시 업데이트 (LangFuse)

### Frontend
- [ ] `speaker` 타입: `"Narrator" | "A" | "B"` → `string` (동적)
- [ ] SpeakerBadge 캐릭터명 표시 (storyboard_characters JOIN 활용)

### 품질
- [ ] 테스트 fixture 전수 업데이트 (37+ 파일)
- [ ] 기존 기능 regression 없음
- [ ] 린트 통과

## 제약
- 변경 파일 10개 이하 목표 (테스트 제외)
- 건드리면 안 되는 것: TTS 엔진 로직 (speaker 매핑만 변경)
- DB 마이그레이션 포함 → DBA 리뷰 필수
- `character_id`/`character_b_id` API 필드 제거는 **Phase B 범위** (이 태스크에서 하지 않음)
- Enum ID 정규화(SP-020) 선행 필요 — structure/language ID가 정규화되어야 speaker ID도 일관성 있게 전환 가능

## 힌트
- 명세: `docs/01_product/FEATURES/SPEAKER_DYNAMIC_ROLE.md`
- 관련 파일: `backend/config.py`, `backend/services/agent/nodes/creative_qc.py`, `backend/services/agent/nodes/_review_validators.py`, `frontend/app/types/index.ts`
- 이미 동적 인프라 완비: `speaker_resolver.py`, `casting_sync.py`, `storyboard_characters` 테이블

## 상세 설계 (How)
> [design.md](./design.md) 참조 (착수 시 작성)
