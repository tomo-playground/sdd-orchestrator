# Shorts Producer

**Shorts Producer**는 쇼츠 영상 콘텐츠 제작을 자동화하는 AI 기반 워크스페이스입니다. **Google Gemini**를 통한 스토리보드 기획, **Stable Diffusion** 기반의 이미지 생성, 그리고 **Qwen-Audio** 기반의 TTS와 **FFmpeg**를 결합하여 고품질의 영상을 자동으로 렌더링합니다.

## 🏗 System Architecture (V3)

시스템은 **V3 관계형 스키마**를 채택하여 캐릭터 일관성과 복합적인 프롬프트 제어를 구현했습니다.

```mermaid
graph TD
    %% Nodes
    User([User])
    
    subgraph Frontend ["Frontend (Next.js)"]
        UI["Web UI (React)"]
        Studio["Studio /studio"]
        Manage["Management /manage"]
    end
    
    subgraph Backend ["Backend (FastAPI)"]
        API["Main API Router"]
        
        subgraph Logic ["Core Logic"]
            Planner["Storyboard Planner (Gemini)"]
            PromptEng["12-Layer Prompt Engine"]
            GenImg["Image Generator (Stable Diffusion)"]
            TTS["TTS Engine (Qwen-Audio)"]
            Renderer["Video Renderer (FFmpeg)"]
        end
        
        subgraph Data ["Data & Assets"]
            DB[("PostgreSQL - V3 Schema")]
            Storage[("Shared Storage (MinIO/S3)")]
            AssetsDir["./assets (Fonts, Overlays, BGM)"]
        end
    end

    subgraph External ["External Services"]
        SD_API["Stable Diffusion WebUI API"]
        Gemini_API["Google Gemini API"]
    end

    %% Connections
    User -->|Topic/Control| UI
    UI <-->|JSON/HTTP| API
    
    API --> Planner
    Planner <--> Gemini_API
    
    API --> PromptEng
    PromptEng --> GenImg
    GenImg <--> SD_API
    
    API --> TTS
    API --> Renderer
    
    Renderer --> AssetsDir
    Renderer --> Storage
```

## 🔄 주요 워크플로우

1.  **AI 기획 (Gemini)**: 주제를 입력하면 씬 구성, 스크립트, 이미지 프롬프트가 포함된 스토리보드를 자동 생성합니다.
2.  **12-레이어 프롬프트 엔진**: 캐릭터의 고유 속성(Trait)과 임시 속성(Outfit)을 분리하여 일관성 있는 이미지를 생성합니다.
3.  **지능형 검수 및 보정**:
    *   **WD14 Tagger**: 생성된 이미지가 프롬프트의 키워드(태그)와 일치하는지 정량적으로 검증합니다.
    *   **Gemini Vision**: 검증 점수가 낮을 경우, 이미지를 시각적으로 분석하여 불일치 요소를 파악하고 자동으로 편집 제안 및 이미지 보정(Pose/Expression 등)을 실행합니다.
4.  **TTS & 합성**: **Qwen-Audio**를 활용한 고품질 TTS와 배경음악, 오버레이를 FFmpeg로 결합하여 MP4 영상을 완성합니다.

## 📂 Project Structure

### Backend (`/backend`)
*   **`routers/`**: 도메인별 API 엔드포인트 (Storyboard, Character, Tag, Video 등).
*   **`services/`**: 핵심 비즈니스 로직 (Prompt Builder, TTS, Video Processing).
*   **`models/`**: SQLModel 기반의 V3 데이터베이스 스키마 정의.
*   **`schemas/`**: Pydantic을 이용한 데이터 요청/응답 규격화.
*   **`tests/`**: 기능별 통합 및 단위 테스트.

### Frontend (`/frontend`)
*   **`app/studio/`**: 영상 제작의 핵심 워크스페이스.
*   **`app/manage/`**: 캐릭터, 태그, LoRA 및 생성된 에셋 관리 UI.
*   **`app/store/`**: Zustand 기반의 글로벌 상태 관리.

## 🚀 Getting Started

### Prerequisites
1.  **Stable Diffusion WebUI**: `--api` 플래그가 활성화된 상태로 `7860` 포트에서 실행 중이어야 합니다.
2.  **Google Gemini API Key**: `.env` 파일에 설정.
3.  **FFmpeg**: 시스템 PATH에 설치되어 있어야 합니다.
4.  **PostgreSQL**: 프로젝트 DB 환경 구축.

### Installation

**Backend:**
```bash
cd backend
# .env 파일 생성 (GEMINI_API_KEY, DATABASE_URL 등)
uv run main.py
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

접속 주소: `http://localhost:3000/studio`

## 📖 Documentation

전체 문서는 `/docs` 디렉토리에서 확인할 수 있습니다.

### 📂 Directory Structure
```
docs/
├── 00_meta/          # 문서 구조 및 정책
├── 01_product/       # PRD, 로드맵, 기능 명세
├── 02_design/        # UI/UX 디자인 에셋
├── 03_engineering/   # DB 스키마, 아키텍처, API 명세
├── 04_operations/    # 배포 및 운영 가이드 (TTS 설정 등)
├── guides/           # 기여 및 개발 가이드
└── 99_archive/       # 아카이브
```

### 🔗 Key Documents

#### 🚀 Product & Planning
- [Roadmap](docs/01_product/ROADMAP.md) - 개발 진행 현황 및 예정 작업
- [PRD](docs/01_product/PRD.md) - 제품 요구사항 정의서
- [Feature Specs](docs/01_product/FEATURES/) - 개별 기능 요구사항 명세

#### 🏗 Engineering
- [System Overview](docs/03_engineering/architecture/SYSTEM_OVERVIEW.md) - 전체 시스템 구조 및 컴포넌트 설명
- [V3 DB Schema](docs/03_engineering/architecture/DB_SCHEMA.md) - 데이터베이스 구조 및 관계도
- [API Reference](docs/03_engineering/api/REST_API.md) - REST API 엔드포인트 명세
- [Render Pipeline](docs/03_engineering/backend/RENDER_PIPELINE.md) - 영상 렌더링 파이프라인 기술 상세
- [Test Strategy](docs/03_engineering/testing/TEST_STRATEGY.md) - 테스트 전략 및 시나리오

#### 🛠 Operations & Guides
- [TTS Setup](docs/04_operations/TTS_SETUP.md) - Qwen-Audio TTS 설정 가이드
- [Deployment Guide](docs/04_operations/DEPLOYMENT.md) - 서버 배포 및 운영 가이드
- [Contributing](guides/CONTRIBUTING.md) - 개발 기여 및 스타일 가이드