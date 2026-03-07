# Multi-Character 지원

> 상태: **완료** (2026-02-11, Multi-Character LoRA 지원 추가)

## 배경

현재 씬당 캐릭터 1명만 지정 가능. 대화 장면, 그룹 씬 등 다중 캐릭터가 필요한 콘텐츠 제작 불가.

## 목표

- 씬당 A, B, C... 다중 캐릭터 배치 지원
- 캐릭터별 독립적 포즈/표정/의상 지정
- 프롬프트 엔진에서 다중 캐릭터 태그 합성

## 구현 완료 항목

### DB 스키마
- `storyboard_characters` 테이블: speaker→character 매핑 (UniqueConstraint: storyboard_id + speaker)
- `scene_character_actions` 테이블: 씬별 캐릭터 액션 태그

### Backend
- `StoryboardRequest.character_b_id`: Dialogue 구조에서 Speaker B 캐릭터 지정
- `_sync_speaker_mappings()`: 저장/업데이트 시 speaker→character 매핑 동기화
- `auto_populate_character_actions()`: Gemini 스토리보드 생성 시 캐릭터 액션 자동 생성
- `_load_character_context()`: Character A/B 각각 로드 → Gemini 템플릿에 전달
- `StoryboardDetailResponse.characters`: 캐스트 정보 (speaker, character_name, reference_image_url) 반환
- `get_storyboard_by_id()`: `storyboard_characters` eager load + characters 리스트 빌드

### Frontend
- `PromptSetupPanel`: Dialogue 모드에서 Character A/B 셀렉터 표시
- `SceneCharacterActions.tsx`: 캐릭터별 액션 태그 그룹 표시/편집/삭제/추가
- `SceneFormFields.tsx`: Dialogue 모드에서 캐릭터 액션 자동 렌더링
- `speakerResolver.ts`: speaker별 character_id, LoRA, IP-Adapter, negative prompt 분기
- `storyboardActions.ts`: 저장 시 `character_b_id` 전송
- `useStudioInitialization.ts`: 로드 시 character_b_id 복원

### 이미지 생성
- speaker="A" 씬은 Character A 태그/LoRA, speaker="B" 씬은 Character B 태그/LoRA 사용
- 현재는 "교대 표시" 방식 (씬별 한 캐릭터). "한 프레임에 2캐릭터"는 SD 기술적 한계로 별도 과제.

### Multi-Character LoRA 지원 (2026-02-11)
- `loras` 테이블에 멀티캐릭터 필드 3개 추가:
  - `is_multi_character_capable` (Boolean): 2인 동시 출연 지원 여부
  - `multi_char_weight_scale` (Numeric(3,2)): 2인 씬에서 LoRA weight 축소 비율
  - `multi_char_trigger_prompt` (String(200)): 멀티캐릭터 전용 호출 프롬프트
- `scenes.scene_mode` (String(10)): `"single"` (1인) or `"multi"` (2인 동시 출연)
- Scene Generate API (`POST /scene/generate`): `character_b_id` 파라미터로 두 번째 캐릭터 지정
- Prompt Compose API (`POST /prompt/compose`): `character_b_id`, `scene_id` 파라미터 추가
- 2인 동시 출연 시 각 LoRA의 `multi_char_weight_scale`로 가중치 자동 축소

## 수락 기준

| # | 기준 | 상태 |
|---|------|------|
| 1 | 씬당 2명 이상 캐릭터 지정 가능 | ✅ |
| 2 | 캐릭터별 독립적 포즈/표정 설정 | ✅ |
| 3 | 생성된 이미지에 다중 캐릭터 반영 | ✅ |
| 4 | 기존 단일 캐릭터 워크플로우 영향 없음 | ✅ |
| 5 | LoRA별 멀티캐릭터 지원 여부 설정 가능 | ✅ |
| 6 | 2인 씬에서 LoRA weight 자동 축소 | ✅ |
