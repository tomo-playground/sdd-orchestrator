# Multi-Character 지원

> 상태: **완료** (2026-02-11 기반 구축, Phase 30-O에서 V-Pred 2인 동시 출연 구현 예정)

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

### Multi-Character LoRA 지원 (2026-02-11) — Phase 30-O에서 제거 예정

> **폐기 예정**: NoobAI-XL V-Pred 전환으로 LoRA 없이도 2인 생성 10/10 성공.
> LoRA 기반 게이트가 실제 능력을 차단하는 병목이 됨. Phase 30-O에서 3필드 DROP 예정.

- ~~`loras` 테이블에 멀티캐릭터 필드 3개~~ → **Phase 30-O에서 제거**:
  - ~~`is_multi_character_capable`~~ — 모델 자체가 지원하므로 불필요
  - ~~`multi_char_weight_scale`~~ — `SCENE_CHARACTER_LORA_SCALE` 상수로 대체 완료
  - ~~`multi_char_trigger_prompt`~~ — 사용 실적 0건
- `scenes.scene_mode` (String(10)): `"single"` (1인) or `"multi"` (2인 동시 출연) — **유지**
- Scene Generate API (`POST /scene/generate`): `character_b_id` 파라미터 — **유지**
- Prompt Compose API (`POST /prompt/compose`): `character_b_id`, `scene_id` 파라미터 — **유지**

### Phase 30-O: V-Pred 2인 동시 출연 (2026-03-14 착수 예정)

- **방식**: 일반 txt2img 프롬프트 (Regional Prompter/Forge Couple/MultiDiffusion V-Pred 미호환)
- **게이트 변경**: LoRA 체크 → Dialogue 구조 + 2캐릭터 존재 조건으로 단순화
- **BLOCKER 방어**: scene_mode=multi 시 ControlNet/IP-Adapter 자동 비활성화
- **상세 계획**: [CHARACTER_CONSISTENCY_V2.md Sub-Phase O](CHARACTER_CONSISTENCY_V2.md)

## 수락 기준

| # | 기준 | 상태 |
|---|------|------|
| 1 | 씬당 2명 이상 캐릭터 지정 가능 | ✅ |
| 2 | 캐릭터별 독립적 포즈/표정 설정 | ✅ |
| 3 | 생성된 이미지에 다중 캐릭터 반영 | ✅ |
| 4 | 기존 단일 캐릭터 워크플로우 영향 없음 | ✅ |
| 5 | ~~LoRA별 멀티캐릭터 지원 여부 설정 가능~~ | ~~✅~~ → Phase 30-O에서 제거 |
| 6 | ~~2인 씬에서 LoRA weight 자동 축소~~ | ~~✅~~ → `SCENE_CHARACTER_LORA_SCALE`로 대체 |
| 7 | **V-Pred 2인 동시 출연 성공률 > 80%** | ✅ 완료 (EXP-1~4 검증, 3후보 보상) |
| 8 | **Multi 씬 ControlNet/IP-Adapter 자동 비활성화** | ✅ 완료 (finalize.py O-2a) |
