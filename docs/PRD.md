# Shorts Factory - Actionable PRD (v2.0)

이 문서는 추상적인 전략이 아닌, **현재 개발 단계에서 구현 및 검증해야 할 실질적인 요구사항**을 정의합니다.
`docs/ROADMAP.md`의 Phase 5, 6, 7 완료 사항을 반영하여 v2.0 기준으로 갱신되었습니다.

## 1. 프로젝트 범위 (Scope & Priorities)

### ✅ v2.0 Core (Current Production)
현재 배포되어 실제 영상 제작에 사용 중인 핵심 기능입니다.
*   **Planning**:
    *   Gemini 스토리보드 생성 + **Danbooru Strict Tag Rule** 적용.
    *   **Preset System**: 일본어/수학 레슨 등 구조화된 템플릿 지원.
*   **Consistency (High Fidelity)**:
    *   **Character Presets**: LoRA + **IP-Adapter (CLIP/FaceID)** 조합으로 얼굴/스타일 고정.
    *   **Prompt History**: 성공한 프롬프트 저장 및 재사용.
*   **Production**:
    *   **Batch Generation**: 3장 동시 생성 및 선택 (Candidates UI).
    *   **Motion**: **Ken Burns Effect** (Zoom/Pan 10종 프리셋) 및 Random 적용.
    *   **Audio**: Edge-TTS (Script) + **Random BGM** + Audio Ducking.
*   **Quality Control**:
    *   **Tag Classification**: DB/Rule 기반 태그 자동 분류 및 검증.
    *   **Evaluation Framework**: Mode A/B 품질 비교 시스템 (`/manage` Eval 탭).

### ⏳ v2.x Backlog (Next Steps)
품질 안정화 및 고도화를 위해 예정된 작업입니다 (`docs/ROADMAP.md` 참조).
*   **Prompt Quality Automation**: Match Rate 자동 측정 및 대시보드화.
*   **Gemini Prompt Verification**: 위험 태그(Danbooru 0건) 자동 감지 및 차단.
*   **Generation Log Analytics**: 성공/실패 패턴 학습 및 추천 시스템.
*   **Multi-Character**: 2인 이상 캐릭터의 대화 및 상호작용 렌더링.
*   **VEO Clip**: Video Generation Model 통합.

---

## 2. 테크니컬 데이터 흐름 (Technical Data Flow)

UI/UX 흐름보다 **데이터가 어떻게 흘러가고 저장되는지**를 정의하여 로직 오류를 방지합니다.

### 2.1. 기획 단계 (Flow: User Input -> State)
*   **Input**: `Topic`, `Character Preset`, `Options(Voice, BGM)`
*   **Process**: `POST /storyboard/create` (Gemini) -> **Tag Validation**
*   **Output State**: `scenes: Scene[]` (JSON Array with Danbooru-verified tags)
*   **Risk**: Gemini의 위험 태그 사용 -> **Action**: 템플릿 내 CRITICAL RULE 명시 및 사후 검증 로직.

### 2.2. 이미지 생성 단계 (Flow: State -> SD API -> File System)
*   **Input**: `Scene.image_prompt` + `Character Preset (LoRA + IP-Adapter Settings)`
*   **Process**:
    1. Frontend: 3x 요청 병렬 전송 (`useAutopilot`).
    2. Backend: `POST /sdapi/v1/txt2img`
       - **Resolution Optimization**: `512x768` (2:3) 고정. (Post/Full 모두 호환)
       - **ControlNet/IP-Adapter** 페이로드 주입.
       - **Tag Conflict Rules** 적용 (충돌 태그 자동 제거).
       - **Strict Tagging**: `full body` 지양 -> `cowboy shot` 권장 (머리 잘림 방지).
    3. Backend: `outputs/images/{timestamp}.png` 저장.
*   **Output State**: `Scene.image_url` (로컬 파일 경로 URL)
*   **Constraint**: **GPU VRAM 8GB 이상 필수**. (IP-Adapter + LoRA 동시 로드 필요)

### 2.3. 렌더링 단계 (Flow: Files -> FFmpeg -> Video)
*   **Input**: `scenes` (이미지), `audio` (TTS/BGM), `motion_config` (Ken Burns)
*   **Process**:
    1. Backend: Edge-TTS로 오디오 생성 (`assets/temp/`).
    2. Backend: `services/motion.py`가 이미지에 Zoom/Pan 효과 적용.
    3. Backend: FFmpeg로 [Motion Video + Subtitle + Audio] 합성.
       - **Layout Handling**:
         - **Full (9:16)**: `512x768` 이미지를 `Cover` 모드로 꽉 채움.
         - **Post (1:1)**: `512x768` 이미지의 **상단(Top)**을 크롭하여 인물 중심 구도 확보.
*   **Risk**: 자막 폰트 렌더링 이슈 -> **Action**: Pixel-based Wrapping 및 폰트 경로 정규화(`resolve_subtitle_font_path`) 적용 완료.

---

## 3. 기술적 제약 및 환경 (Constraints & Environment)

### 3.1. 필수 실행 환경
*   **Stable Diffusion WebUI**:
    *   API 모드 (`--api`) 실행.
    *   **ControlNet Extension** 설치 필수.
    *   **IP-Adapter Models** (`ip-adapter-plus_sd15.safetensors` 등) 확보.
*   **Backend**: Python 3.10+, `ffmpeg` 시스템 경로 설정.
*   **Database**: PostgreSQL (로컬/Docker) - 태그, 캐릭터, 히스토리 관리용.

### 3.2. 성능 한계 (Known Limitations)
*   **속도**: 로컬 GPU 성능 의존. (ControlNet 활성화 시 생성 시간 20~30% 증가)
*   **스토리지**: `outputs/` 자동 정리 정책 필요 (Storage Cleanup 구현됨).

---

## 4. 완료 기준 (Definition of Done)

다음 체크리스트를 모두 통과해야 작업이 완료된 것으로 간주합니다.

1.  [x] **Autopilot Stability**: 주제 입력부터 렌더링까지 중단 없이 완주되는가? (Smart AutoRun 검증)
2.  [x] **Character Consistency**:
    *   생성된 모든 장면에서 캐릭터의 외형(LoRA)이 유지되는가?
    *   **IP-Adapter**가 얼굴/헤어스타일을 일관되게 고정하는가?
3.  [x] **Motion Quality**:
    *   정지 이미지에 **Ken Burns Effect**가 자연스럽게 적용되었는가?
    *   영상 전환 시 끊김이나 글리치가 없는가?
4.  [x] **Rendering Integrity**:
    *   최종 `.mp4` 파일에 TTS, BGM(Ducking 적용), 자막이 싱크에 맞게 포함되었는가?
5.  [x] **Resolution Strategy**:
    *   `512x768` 해상도로 이미지가 생성되는가?
    *   1:1(Post) 렌더링 시 머리가 잘리지 않고 적절히 크롭되는가?