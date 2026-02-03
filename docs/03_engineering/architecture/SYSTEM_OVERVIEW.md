# System Overview

## Abstract
Shorts Producer 시스템의 고수준 아키텍처 다이어그램 및 컴포넌트 간 상호작용 흐름을 다룹니다.

## 1. Architectural Diagram

시스템은 크게 사용자와 소통하는 **Frontend**, 핵심 비즈니스 로직을 수행하는 **Backend**, 그리고 외부 AI 서비스 계층으로 구성됩니다.

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
            StorySvc["Storyboard Service (Gemini)"]
            PromptSvc["V3 Prompt Engine"]
            ImageSvc["Image Generation Service"]
            VideoSvc["Video Render Pipeline"]
            TTSSvc["TTS Service (Qwen-Audio)"]
            ValidationSvc["Intelligent Validation (WD14/Vision)"]
        end

        subgraph Data ["Data & Persistence"]
            DB[("PostgreSQL (SQLAlchemy/SQLModel)")]
            MinIO[("Object Storage (MinIO/S3)")]
            FS["Local File System"]
        end
    end

    subgraph External ["External AI Services"]
        Gemini["Google Gemini API (Text/Vision)"]
        SD["Stable Diffusion WebUI API"]
    end

    %% Interaction Flows
    User --> UI
    UI <--> Router
    Router --> Services
    
    StorySvc <--> Gemini
    PromptSvc --> ImageSvc
    ImageSvc <--> SD
    VideoSvc --> FS
    VideoSvc --> MinIO
    
    Services <--> DB
    Services <--> MinIO
```

## 2. 핵심 데이터 흐름 (System Data Flow)

서비스의 주요 워크플로우를 관통하는 데이터 흐름도입니다.

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant AI as External AI
    participant DB as Database

    U->>F: 주제 입력 (Create Storyboard)
    F->>B: POST /storyboards/create
    B->>AI: Gemini: 기획 요청
    AI-->>B: 씬 구성 및 프롬프트 반환
    B->>DB: 스토리보드 데이터 영속화
    B-->>F: Storyboard JSON 반환

    F->>B: 이미지 생성 요청 (Batch)
    B->>B: V3 Prompt Engine: 프롬프트 조합
    B->>AI: SD API: 이미지 생성
    AI-->>B: 이미지 바이너리
    B->>DB: 에셋 등록 및 로그 기록
    B-->>F: Image URL 반환

    F->>B: 최종 영상 렌더링 요청
    B->>B: Render Pipeline: TTS + FFmpeg
    B->>DB: 최종 비디오 에셋 등록
    B-->>F: Video URL 반환
```
