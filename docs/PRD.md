# Shorts Factory - Actionable PRD (v1.0)

이 문서는 추상적인 전략이 아닌, **현재 개발 단계에서 구현 및 검증해야 할 실질적인 요구사항**을 정의합니다.

## 1. 프로젝트 범위 (Scope & Priorities)

### ✅ v1.0 Core (Must Have) - *현재 구현 목표*
이 기능들이 동작하지 않으면 배포/사용 불가로 간주합니다.
*   **Planning**: 주제 입력 -> Gemini 스토리보드 생성 -> 편집(Script 수정).
*   **Consistency**: `Character DNA Builder`를 통한 프롬프트 고정.
*   **Production**:
    *   3장 생성 후 택1 (Candidates UI).
    *   `Auto Fix` 및 `Clean Prompts` 로직.
    *   SD 1.5 기반 이미지 생성.
*   **Output**: FFmpeg를 이용한 `.mp4` 렌더링 (TTS, 자막, 배경음악 포함).
*   **Format**: 9:16(Full) 및 1:1(Post) 레이아웃 지원.

### ⏳ v1.x Backlog (Nice to Have) - *추후 개발*
*   VEO Clip (Video Generation).
*   ControlNet (IP-Adapter) 얼굴 고정.
*   SQLite 데이터베이스 연동.
*   정량적 품질 지표(Match Rate 자동화 등).

---

## 2. 테크니컬 데이터 흐름 (Technical Data Flow)

UI/UX 흐름보다 **데이터가 어떻게 흘러가고 저장되는지**를 정의하여 로직 오류를 방지합니다.

### 2.1. 기획 단계 (Flow: User Input -> State)
*   **Input**: `Topic`, `Options(Voice, BGM)`
*   **Process**: `POST /storyboard/create` (Gemini)
*   **Output State**: `scenes: Scene[]` (JSON Array in React State)
*   **Risk**: Gemini API 타임아웃 → **Action**: 30초 타임아웃 설정 및 재시도 UI 제공.

### 2.2. 이미지 생성 단계 (Flow: State -> SD API -> File System)
*   **Input**: `Scene.image_prompt` + `Character DNA(Base Prompt)`
*   **Process**: 
    1. Frontend: 3x 요청 병렬 전송.
    2. Backend: `POST /sdapi/v1/txt2img` -> Base64 수신.
    3. Backend: `outputs/images/{timestamp}.png` 저장.
*   **Output State**: `Scene.image_url` (로컬 파일 경로 URL)
*   **Constraint**: **GPU VRAM 8GB 이상 권장**. (VRAM 부족 시 3장 생성 속도 저하 발생 가능)

### 2.3. 렌더링 단계 (Flow: Files -> FFmpeg -> Video)
*   **Input**: `scenes` (이미지 경로들), `audio` (TTS/BGM), `layout_style`
*   **Process**:
    1. Backend: Edge-TTS로 오디오 파일 생성 (`assets/temp/`).
    2. Backend: FFmpeg 명령어로 이미지+오디오+자막 합성.
*   **Risk**: 한글 폰트 깨짐 (Mac NFD 문제) → **Action**: `resolve_subtitle_font_path`의 정규화 로직 필수 검증.

---

## 3. 기술적 제약 및 환경 (Constraints & Environment)

### 3.1. 필수 실행 환경
*   **Stable Diffusion WebUI**: 로컬 포트 `7860`에서 실행 중이어야 함 (`--api` 옵션 필수).
*   **Backend**: Python 3.10+, `ffmpeg` 시스템 경로 설정 필수.
*   **Assets**: `backend/assets/fonts/` 내에 한글 폰트(`.ttf`) 필수 존재.

### 3.2. 성능 한계 (Known Limitations)
*   **속도**: 로컬 GPU 성능에 전적으로 의존. (RTX 3060 기준 이미지 1장당 약 5~8초 소요)
*   **스토리지**: 생성된 이미지는 로컬 `outputs/` 폴더에 쌓임. Storage Cleanup API (`/storage/cleanup`)로 정리 가능.

---

## 4. 완료 기준 (Definition of Done)

다음 체크리스트를 모두 통과해야 작업이 완료된 것으로 간주합니다.

1.  [x] **Autopilot**: 주제 입력 후 '이미지 생성 완료' 단계까지 멈춤 없이 진행되는가? ✅
2.  [x] **Consistency**: 생성된 3개 이상의 장면에서 캐릭터의 **머리색과 옷**이 `Base Prompt` 설정대로 유지되는가? ✅
3.  [x] **Rendering**: 최종 비디오 파일이 생성되고, **소리(TTS+BGM)**가 정상적으로 들리는가? ✅
4.  [x] **UI Resilience**: 새로고침(F5)을 해도 작업하던 내용(Draft)이 복구되는가? ✅