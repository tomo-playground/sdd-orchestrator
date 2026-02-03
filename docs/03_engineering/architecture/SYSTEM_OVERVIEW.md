# System Overview

## Abstract
Shorts Producer 시스템의 고수준 아키텍처 다이어그램 및 컴포넌트 간 상호작용 흐름을 다룹니다.

## 1. Architectural Diagram

시스템은 프론트엔드, 백엔드, 그리고 수동 구축되는 로컬 AI(SD WebUI)와 클라우드 AI(Gemini) 계층으로 세분화됩니다.

```mermaid
graph TB
    subgraph Client ["Client Side"]
        User([User])
        UI["Web UI (Next.js/React)"]
        Store["State Management (Zustand)"]
    end

    subgraph Backend ["Backend (FastAPI)"]
        Router["API Router (Endpoints)"]
        
        subgraph Services ["Core Services"]
            StorySvc["Storyboard Service"]
            PromptSvc["V3 Prompt Engine"]
            ImageSvc["Image Generation Service"]
            VideoSvc["Video Render Pipeline"]
            TTSSvc["TTS Service (Qwen3-TTS)"]
            ValidationSvc["Validation (WD14/Vision)"]
        end

        subgraph Data ["Data & Persistence"]
            DB[("PostgreSQL")]
            MinIO[("MinIO (Object Storage)")]
            FS["Local Sys (Temporary)"]
        end
    end

    subgraph CloudAI ["Cloud AI (External)"]
        Gemini["<b>Google Gemini API</b><br/>(Text/Vision/Translation)"]
    end

    subgraph LocalAI ["Local AI (Self-Hosted)"]
        SD["<b>Stable Diffusion WebUI</b><br/>(A1111 API)"]
        CN["ControlNet / IP-Adapter"]
        WD14["WD14 ONNX Tagger"]
        Qwen["Qwen3-TTS Engine"]
    end

    %% Interaction Flows
    User --> UI
    UI <--> Router
    Router --> Services
    
    StorySvc <--> Gemini
    PromptSvc --> ImageSvc
    ImageSvc <--> SD
    SD <--> CN
    VideoSvc --> FS
    VideoSvc --> MinIO
    VideoSvc --> Qwen
    
    ValidationSvc <--> WD14
    ValidationSvc <--> Gemini
    
    Services <--> DB
    Services <--> MinIO
```

## 2. 핵심 데이터 흐름 (System Data Flow)

서비스의 주요 워크플로우를 관통하는 데이터 흐름도입니다. 외부 API 연동 부위가 Gemini와 WebUI로 명확히 분리됩니다.

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant Gem as Gemini API
    participant SD as SD WebUI (A1111)
    participant DB as Database

    U->>F: 주제 입력 (Create Storyboard)
    F->>B: POST /storyboards/create
    B->>Gem: 기획 요청
    Gem-->>B: 씬 구성 및 프롬프트 반환
    B->>DB: 스토리보드 데이터 영속화
    B-->>F: Storyboard JSON 반환

    F->>B: 이미지 생성 요청 (Batch)
    B->>B: V3 Prompt Engine: 프롬프트 조합
    B->>SD: txt2img API 요청
    SD-->>B: 이미지 바이너리
    B->>Gem: Vision: 이미지 품질 검수 (옵션)
    B->>DB: 에셋 등록 및 로그 기록
    B-->>F: Image URL 반환

    F->>B: 최종 영상 렌더링 요청
    B->>B: Render Pipeline: TTS + FFmpeg
    B->>DB: 최종 비디오 에셋 등록
    B-->>F: Video URL 반환
```

## 3. 기술 스택 (Tech Stack)

### Core
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, Zustand
- **Backend**: FastAPI, Python 3.12, SQLModel (SQLAlchemy)

### AI & Media
- **LLM/LVM**: Google Gemini 2.0 Flash (Storyboard, Prompt, Vision)
- **Image**: Stable Diffusion WebUI (A1111) + ControlNet v1.1 + IP-Adapter Plus
- **TTS**: Qwen3-TTS (12Hz-1.7B-VoiceDesign)
- **Validation**: WD14 (Waifu Diffusion v1.4) Vit-Tagger-v2 (ONNX)
- **Video**: FFmpeg (Filter complex, Ken Burns effect)

### Infrastructure
- **Database**: PostgreSQL (Relational Data)
- **Storage**: MinIO (S3 Compatible Object Storage)
- **Environment**: Docker, uv (Python Package Manager)
