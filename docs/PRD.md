# Shorts Factory - Actionable PRD (v3.0)

이 문서는 추상적인 전략이 아닌, **현재 개발 단계에서 구현 및 검증해야 할 실질적인 요구사항**을 정의합니다.
V3 아키텍처 전환 (Storyboard-Centric + DB-Driven) 완료를 반영하여 v3.0 기준으로 갱신되었습니다.

## 변경 이력

| 버전 | 날짜 | 주요 변경사항 |
|------|------|--------------|
| v3.0 | 2026-01-30 | V3 아키텍처: Storyboard-Centric, 12-Layer Prompt, DB-Driven 태그 시스템 |
| v2.0 | 2026-01-27 | Character Presets, IP-Adapter, Ken Burns, Evaluation Framework |

---

## 1. 프로젝트 범위 (Scope & Priorities)

### v3.0 Core (Current Production)
현재 배포되어 실제 영상 제작에 사용 중인 핵심 기능입니다.

*   **Architecture**:
    *   **Storyboard-Centric**: Storyboard → Scene → CharacterAction 계층 구조로 데이터 영속화.
    *   **V3 Relational Tags**: `character_tags`, `scene_tags`, `scene_character_actions` 연관 테이블.
    *   **Activity Logs**: 생성 이력 + 즐겨찾기 통합 (`activity_logs` 테이블).
*   **Planning**:
    *   Gemini 스토리보드 생성 + **Danbooru Strict Tag Rule** 적용.
    *   스토리보드 DB 저장/조회 (`POST /storyboards`, `GET /storyboards`).
*   **Prompt Engine**:
    *   **12-Layer PromptBuilder**: 태그의 `default_layer` (0-11)에 따라 자동 배치 및 정렬.
    *   **DB-Driven 규칙**: 충돌(`tag_rules`), 별칭(`tag_aliases`), 필터(`tag_filters`) 모두 DB 관리.
    *   **4개 런타임 캐시**: TagCategory, TagAlias, TagRule, LoRATrigger (startup 시 초기화).
    *   **Prompt History**: 성공한 프롬프트 저장 및 재사용.
*   **Consistency (High Fidelity)**:
    *   **Character Presets**: LoRA + **IP-Adapter (CLIP/FaceID)** 조합으로 얼굴/스타일 고정.
    *   **V3 Character Tags**: `is_permanent` (identity vs clothing) 구분으로 태그 관리.
*   **Production**:
    *   **Batch Generation**: 3장 동시 생성 및 선택 (Candidates UI).
    *   **Motion**: **Ken Burns Effect** (Zoom/Pan 10종 + Vertical 6종 프리셋) 및 Random 적용.
    *   **Transitions**: 13개 씬 전환 효과 (fade, wipe, slide, circle, random).
    *   **Audio**: Edge-TTS (Script) + **Random BGM** + Audio Ducking.
*   **Quality Control**:
    *   **Tag Classification**: DB/Rule 기반 태그 자동 분류 (24개 카테고리).
    *   **Evaluation Framework**: Mode A/B 품질 비교 시스템 (`/manage` Eval 탭).
    *   **Admin API**: DB 마이그레이션, 캐시 리프레시 엔드포인트.

### v3.x Backlog (Next Steps)
품질 안정화 및 고도화를 위해 예정된 작업입니다 (`docs/ROADMAP.md` 참조).
*   **Multi-Character UI**: 2인 이상 캐릭터의 대화 및 상호작용 (DB 스키마 완료, UI 대기).
*   **Scene Builder UI**: 장면별 배경/시간/날씨 컨텍스트 태그 선택 UI.
*   **Gemini Auto Edit Phase 2**: Match Rate 낮은 씬 자동 편집 + 대시보드.
*   **Character Consistency Production**: Backend API 확장 + Frontend UI + Multi-Char.
*   **VEO Clip**: Video Generation Model 통합.

---

## 2. 테크니컬 데이터 흐름 (Technical Data Flow)

UI/UX 흐름보다 **데이터가 어떻게 흘러가고 저장되는지**를 정의하여 로직 오류를 방지합니다.

### 2.1. 기획 단계 (Flow: User Input -> Storyboard)
*   **Input**: `Topic`, `Character Preset`, `Options(Voice, BGM)`
*   **Process**: `POST /storyboards/create` (Gemini) -> **Tag Validation**
*   **Output State**: `scenes: Scene[]` (JSON Array with Danbooru-verified tags)
*   **Persistence**: `POST /storyboards` → DB 저장 (Storyboard → Scene → SceneTag/CharacterAction)
*   **Risk**: Gemini의 위험 태그 사용 -> **Action**: 템플릿 내 CRITICAL RULE 명시 + `tag_aliases` 자동 치환.

### 2.2. 이미지 생성 단계 (Flow: State -> Prompt Engine -> SD API -> File System)
*   **Input**: `Scene.image_prompt` + `Character Tags (V3 Relational)` + `LoRA Settings`
*   **Process**:
    1. Frontend: 3x 요청 병렬 전송 (`useAutopilot`).
    2. Backend: **V3 PromptBuilder** (12-Layer 배치)
       - Layer 0-6: Quality → Subject → Identity → Body → Cloth → Accessory
       - BREAK (LoRA 사용 시)
       - Layer 7-11: Expression(1.1x) → Action(1.1x) → Camera → Environment → Atmosphere
    3. Backend: `tag_aliases` 자동 치환, `tag_rules` 충돌 제거, `tag_filters` 필터링.
    4. Backend: `POST /sdapi/v1/txt2img`
       - **Resolution**: `512x768` (2:3) 고정.
       - **ControlNet/IP-Adapter** 페이로드 주입.
    5. Backend: `outputs/images/{timestamp}.png` 저장.
    6. Backend: `POST /activity-logs` → 생성 이력 DB 기록.
*   **Output State**: `Scene.image_url` (로컬 파일 경로 URL)
*   **Constraint**: **GPU VRAM 8GB 이상 필수**. (IP-Adapter + LoRA 동시 로드 필요)

### 2.3. 렌더링 단계 (Flow: Files -> FFmpeg -> Video)
*   **Input**: `scenes` (이미지), `audio` (TTS/BGM), `motion_config` (Ken Burns)
*   **Process**:
    1. Backend: Edge-TTS로 오디오 생성 (`assets/temp/`).
    2. Backend: `services/motion.py`가 이미지에 Zoom/Pan 효과 적용.
    3. Backend: FFmpeg로 [Motion Video + Subtitle + Transition + Audio] 합성.
       - **Layout Handling**:
         - **Full (9:16)**: `512x768` 이미지를 `Cover` 모드로 꽉 채움.
         - **Post (1:1)**: `512x768` 이미지의 **상단(Top)**을 크롭하여 인물 중심 구도 확보.
*   **Risk**: 자막 폰트 렌더링 이슈 -> **Action**: Pixel-based Wrapping 및 폰트 경로 정규화 적용 완료.

---

## 3. 기술적 제약 및 환경 (Constraints & Environment)

### 3.1. 필수 실행 환경
*   **Stable Diffusion WebUI**:
    *   API 모드 (`--api`) 실행.
    *   **ControlNet Extension** 설치 필수.
    *   **IP-Adapter Models** (`ip-adapter-plus_sd15.safetensors` 등) 확보.
*   **Backend**: Python 3.10+, `ffmpeg` 시스템 경로 설정.
*   **Database**: PostgreSQL (로컬/Docker)
    *   V3 Schema: storyboards, scenes, character_tags, scene_tags, scene_character_actions, activity_logs, tag_rules, tag_aliases, tag_filters
    *   마이그레이션: Alembic (V3 Baseline 통합)

### 3.2. 성능 한계 (Known Limitations)
*   **속도**: 로컬 GPU 성능 의존. (ControlNet 활성화 시 생성 시간 20~30% 증가)
*   **스토리지**: `outputs/` 자동 정리 정책 적용 (Storage Cleanup).
*   **캐시**: 4개 런타임 캐시는 startup 시 1회 로드. 변경 시 `/admin/refresh-caches` 호출 필요.

---

## 4. 완료 기준 (Definition of Done)

다음 체크리스트를 모두 통과해야 작업이 완료된 것으로 간주합니다.

1.  [x] **Autopilot Stability**: 주제 입력부터 렌더링까지 중단 없이 완주되는가? (Smart AutoRun 검증)
2.  [x] **Character Consistency**:
    *   생성된 모든 장면에서 캐릭터의 외형(LoRA)이 유지되는가?
    *   **IP-Adapter**가 얼굴/헤어스타일을 일관되게 고정하는가?
3.  [x] **Prompt Quality**:
    *   12-Layer PromptBuilder가 태그를 올바른 순서로 배치하는가?
    *   Tag 충돌 규칙이 DB에서 정상 로드되어 적용되는가?
    *   위험 태그가 `tag_aliases`로 자동 치환되는가?
4.  [x] **Motion Quality**:
    *   정지 이미지에 **Ken Burns Effect**가 자연스럽게 적용되었는가?
    *   영상 전환 시 끊김이나 글리치가 없는가?
5.  [x] **Rendering Integrity**:
    *   최종 `.mp4` 파일에 TTS, BGM(Ducking 적용), 자막이 싱크에 맞게 포함되었는가?
6.  [x] **Resolution Strategy**:
    *   `512x768` 해상도로 이미지가 생성되는가?
    *   1:1(Post) 렌더링 시 머리가 잘리지 않고 적절히 크롭되는가?
7.  [x] **Data Persistence**:
    *   스토리보드/씬이 DB에 정상 저장되는가?
    *   생성 이력이 `activity_logs`에 기록되는가?

---

**참고 문서**:
- API 명세: `docs/specs/API_SPEC.md`
- DB 스키마: `docs/specs/DB_SCHEMA.md`
- 프롬프트 설계: `docs/specs/PROMPT_SPEC.md`
- 로드맵: `docs/ROADMAP.md`
