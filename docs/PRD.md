# Product Requirements Document (PRD): Shorts Factory

## 1. 개요 (Overview)
**Shorts Factory**는 숏폼 영상(Shorts, Reels, TikTok) 제작을 위한 **AI 기반 올인원 스튜디오**입니다. 
사용자가 주제나 대본을 입력하면, AI가 스토리보드를 짜고, 일관성 있는 캐릭터 이미지를 생성하며, 최종적으로 영상으로 렌더링하는 전 과정을 지원합니다.

## 2. 핵심 철학 (Core Philosophy)
1.  **Identity Locking (일관성)**: 영상 내내 캐릭터의 외모(DNA)가 변하지 않아야 한다. 이를 위해 `Base Prompt`와 `Character Builder`를 활용하여 고유 특징을 고정한다.
2.  **Quality First (품질)**: 단순히 생성하는 것을 넘어, '쓸 수 있는' 퀄리티를 보장한다. 이를 위해 **Candidate System(3장 생성 후 선택)**과 **Hi-Res Fix**를 기본으로 채택한다.
3.  **Hybrid Workflow (협업)**: AI가 초안(Autopilot)을 잡지만, 인간이 디테일(Scene Director)을 수정할 수 있는 유연한 구조를 지향한다.

## 3. 주요 기능 (Key Features)

### 3.1. 기획 및 스토리보드 (Planning)
*   **Storyboard Generator**: 주제(Topic)만 입력하면 LLM(Gemini)이 장면별 대본과 프롬프트를 자동으로 작성.
*   **Autopilot Mode**: 기획부터 이미지 생성까지 원클릭으로 진행 (검수를 위해 렌더링 직전 정지).
*   **Audio Hub**: 내레이션(TTS) 성우 선택 및 BGM 미리듣기/선택.

### 3.2. 캐릭터 및 연출 (Directing)
*   **Character DNA Builder (🪄)**:
    *   캐릭터의 외모(헤어, 눈, 체형)와 스타일(화풍)을 태그 기반으로 조합하여 `Base Prompt` 생성.
    *   LoRA 및 Embedding 선택 지원.
*   **Scene Director (🎬)**:
    *   각 장면의 `Positive Prompt` 옆에 위치.
    *   카메라 앵글(Shot type), 조명(Lighting), 동작(Action), 장소(Location)를 클릭으로 조합하여 연출.

### 3.3. 이미지 생성 및 검수 (Production)
*   **Candidate System**:
    *   장면당 **3장의 이미지**를 동시 생성.
    *   프롬프트 일치도가 가장 높은 이미지를 자동 추천하며, 사용자가 썸네일을 클릭해 변경 가능.
*   **Analyze Visual Result**:
    *   생성된 이미지를 AI(WD14/Gemini Vision)가 역으로 분석.
    *   **Match Rate (%)** 표시 및 누락된 태그(Missing Tags) 리포트 제공.
*   **Prompt Optimization**:
    *   **Auto Fix**: 중복된 태그 제거 및 필수 요소(배경, 동작) 보강.
    *   **Clean Prompts**: `Base Prompt`와 중복되는 단어를 장면 프롬프트에서 일괄 삭제.

### 3.4. 영상 렌더링 (Post-Production)
*   **Rendering Engine**: FFmpeg 기반의 고성능 렌더링.
*   **Formats**:
    *   **Full (9:16)**: 모바일 꽉 찬 화면.
    *   **Post (1:1)**: 인스타그램/카드뉴스 스타일 (상단 헤더 + 하단 캡션).
*   **Elements**:
    *   **TTS**: Edge-TTS 기반의 자연스러운 한국어 음성 합성.
    *   **Subtitles**: `온글잎 박다현체` 등 감성 폰트 자동 자막 생성.
    *   **Overlay**: 채널명, 좋아요 수, 아바타 등이 포함된 SNS 스타일 오버레이 자동 합성.

## 4. 기술 스펙 (Technical Specs)

### Frontend
*   **Framework**: Next.js 14 (App Router)
*   **Styling**: Tailwind CSS (Zinc/Emerald/Rose 테마)
*   **Icons**: Lucide React

### Backend
*   **Framework**: Python FastAPI
*   **AI Models**:
    *   **Image**: Stable Diffusion WebUI API (SD 1.5/XL)
    *   **LLM**: Google Gemini Pro (스토리보드, 프롬프트 리라이팅)
    *   **Vision**: WD14 Tagger / Gemini Vision (이미지 분석)
*   **Media Processing**:
    *   **Video**: FFmpeg (이미지+오디오+자막 합성, Pan/Zoom 효과)
    *   **Audio**: Edge-TTS

## 5. 데이터 구조 (Data Structure)
*   **Storage**: 로컬 파일 시스템 (`outputs/`, `assets/`)
*   **Persistence**: `localStorage`를 이용한 작업 상태(Draft) 자동 저장.
*   **Keywords**: `backend/keywords.json`을 통한 태그 관리 및 학습 시스템.

## 6. 향후 계획 (Roadmap)
*   [ ] **VEO Clip**: 정지 이미지를 영상(Video-to-Video)으로 변환하는 기능 통합.
*   [ ] **Prompt Splitter**: 외부 프롬프트 붙여넣기 시 Base/Scene 자동 분리 UI 복구.
*   [ ] **Multi-Language**: 다국어 자막 및 UI 지원.
