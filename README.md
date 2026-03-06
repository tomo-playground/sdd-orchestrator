# Shorts Producer

**Shorts Producer**는 쇼츠 영상 콘텐츠 제작을 자동화하는 AI 기반 워크스페이스입니다. **LangGraph** 기반 Agentic AI Pipeline에서 **Google Gemini**가 스토리보드를 기획하고, **Stable Diffusion**으로 이미지를 생성하며, **Qwen3-TTS (12Hz)**로 음성을 합성하고, **FFmpeg**로 최종 영상을 렌더링합니다.

## System Architecture

시스템은 **V3 관계형 스키마** + **LangGraph Agentic Pipeline**을 채택하여, 여러 AI 에이전트가 자율적으로 협업하며 고품질 영상을 생성합니다.

```mermaid
graph TB
    User([User])

    subgraph Frontend ["Frontend — Next.js 16 · React 19"]
        direction TB
        Pages["Pages: Home · Studio · Scripts · Library · Settings"]
        Store["Zustand 4-Store<br/>Context · Storyboard · Render · UI"]
        Hooks["25 Custom Hooks"]
        Pages --- Store --- Hooks
    end

    subgraph Backend ["Backend — FastAPI · Python 3.13"]
        API["29 REST API Routers"]

        subgraph Pipeline ["Agentic Pipeline — LangGraph"]
            direction LR
            Nodes["19 Agent Nodes<br/>Director Plan · Plan Gate · Writer<br/>Critic · Research · Cinematographer<br/>Review · Sound · TTS ..."]
            Tools["9 Gemini Tools<br/>Research 5 + Cine 4"]
            Nodes --- Tools
        end

        subgraph Services ["Core Services"]
            direction LR
            Prompt["12-Layer<br/>Prompt Engine"]
            ImgGen["Image<br/>Generator"]
            TTS["Qwen3-TTS<br/>Local MPS"]
            Render["FFmpeg<br/>Renderer"]
        end

        API --> Pipeline
        API --> Services
    end

    subgraph Infra ["Infrastructure"]
        direction LR
        DB[("PostgreSQL<br/>26 Models · Alembic")]
        S3[("MinIO / S3<br/>Media Storage")]
        LangFuse["LangFuse<br/>Observability"]
    end

    subgraph External ["External APIs"]
        direction LR
        SD["SD WebUI<br/>SDXL · ControlNet<br/>IP-Adapter"]
        Gemini["Google Gemini<br/>Function Calling"]
    end

    User <-->|"HTTP · SSE"| Frontend
    Frontend <-->|"REST JSON"| API

    Pipeline <-->|"Function Calling"| Gemini
    ImgGen <-->|"txt2img · img2img"| SD
    Render -->|"Upload"| S3
    Pipeline -.->|"Trace"| LangFuse
    API <--> DB
    Services <--> DB
```

### Agentic Pipeline Flow

19개 에이전트 노드가 **Interaction Mode** (Auto/Guided/Hands-on)와 **skip_stages** 파라미터에 따라 자율 협업합니다. Director가 Plan→Checkpoint→ReAct Loop으로 품질을 관리하고, Score 기반 라우팅으로 안전망을 제공합니다.

```mermaid
flowchart TD
    START(("START"))

    START -->|"skip_stages 직접 지정"| writer
    START -->|"기본"| director_plan["Director Plan<br/>목표 수립"]

    director_plan --> director_plan_gate{"Plan Gate"}
    director_plan_gate -->|"Plan 승인"| inventory_resolve
    director_plan_gate -.->|"Plan 반려/수정"| director_plan
    
    inventory_resolve --> research["Research<br/>5 Tools · Memory Store"]
    research --> critic["Critic<br/>3-Architect Debate"]
    critic --> concept_gate{"Concept<br/>Gate"}
    concept_gate -->|"Select"| writer["Writer<br/>Planning + Script Gen"]
    concept_gate -.->|"Regenerate"| critic

    writer --> review["Review<br/>Rule + Gemini + NarrativeScore"]

    review -->|"Pass · Full"| checkpoint["Director Checkpoint<br/>Score-Based Gate"]
    review -->|"Pass · Quick"| finalize["Finalize<br/>Merge Results"]
    review -->|"Fail"| revise["Revise<br/>History 누적 + Re-gen"]
    revise --> review

    checkpoint -->|"Proceed (≥0.7)"| cine["Cinematographer<br/>4 Tools · Danbooru Tags"]
    checkpoint -.->|"Revise (<0.7)"| writer

    cine --> fan{"Fan-out"}
    fan --> tts["TTS Designer"]
    fan --> sound["Sound Designer"]
    fan --> copyright["Copyright Reviewer"]

    tts --> director
    sound --> director
    copyright --> director["Director<br/>ReAct 3-Step · Message Protocol"]

    director -->|"Approve"| human{"Human<br/>Gate"}
    director -.->|"Revise Script"| revise
    director -.->|"Revise Production"| cine

    human -->|"Approve"| finalize
    human -.->|"Revise"| revise

    finalize -->|"Full"| explain["Explain<br/>Creative Reasoning"]
    finalize -->|"Quick"| learn
    explain --> learn["Learn<br/>Memory Update"]
    learn --> DONE(("END"))

    style START fill:#4CAF50,color:#fff
    style DONE fill:#4CAF50,color:#fff
    style fan fill:#FF9800,color:#fff
    style concept_gate fill:#2196F3,color:#fff
    style checkpoint fill:#9C27B0,color:#fff
    style human fill:#2196F3,color:#fff
    style director fill:#9C27B0,color:#fff
    style director_plan fill:#9C27B0,color:#fff
```

## 주요 기능

1.  **Agentic AI Pipeline**: Director, Writer, Critic, Research, Cinematographer 등 19개 에이전트 노드가 LangGraph 기반으로 자율 협업하며 스토리보드를 창작합니다.
    - 3단계 협업형 UX (Auto/Guided/Hands-on) 및 Stage-Level Skip 지원
    - Revision History 누적 (동일 실패 반복 방지), 최대 리비전 3회
    - Tool-Calling (Gemini Function Calling 9개), 3-Architect Debate, NarrativeScore
2.  **12-Layer Prompt Engine**: 캐릭터의 고유 속성(Trait)과 임시 속성(Outfit)을 분리하여 일관성 있는 이미지를 생성합니다.
3.  **지능형 검수**:
    - **WD14 Tagger**: 생성 이미지와 프롬프트 키워드 일치 여부를 정량 검증합니다.
    - **Gemini Vision**: 검증 점수가 낮으면 이미지를 시각 분석하여 보정합니다.
4.  **TTS & 렌더링**: Qwen3-TTS (12Hz) 로컬 음성 합성 (오디오 정규화) + AI BGM + FFmpeg 영상 합성으로 최종 영상을 완성합니다.
5.  **스마트 렌더링**: 얼굴 감지 기반 크롭, 동적 Scene Text 높이, 플랫폼별 Safe Zone, 배경 밝기 기반 텍스트 색상 자동 조정.

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| Backend | FastAPI, Python 3.13 |
| Frontend | Next.js 16, React 19, Zustand 5, Tailwind CSS 4 |
| DB | PostgreSQL, SQLAlchemy, Alembic |
| AI Pipeline | LangGraph, Google Gemini (`google-genai`), 30 Jinja2 Templates |
| Image Gen | Stable Diffusion WebUI (SDXL), ControlNet, IP-Adapter |
| TTS | Qwen3-TTS (12Hz, 로컬 MPS) |
| Video | FFmpeg (Ken Burns, 13종 전환 효과) |
| Storage | MinIO/S3 |
| Observability | LangFuse (셀프호스팅) |
| Testing | pytest (Backend), Vitest (Frontend), Playwright (VRT/E2E) |

## Project Structure

### Backend (`/backend`)
```
backend/
├── routers/          # 도메인별 API 엔드포인트 (29개 라우터)
├── services/
│   ├── agent/        # LangGraph Agentic Pipeline
│   │   ├── nodes/    #   19개 에이전트 노드 + 5개 유틸리티 모듈
│   │   ├── tools/    #   Gemini Function Calling 9개 도구
│   │   ├── state.py  #   ScriptState (Graph State)
│   │   └── routing.py#   8개 조건부 라우팅 함수
│   ├── video/        # FFmpeg 렌더링 파이프라인
│   ├── prompt/       # 12-Layer Prompt Builder
│   ├── keywords/     # 태그 시스템 (캐시, 검증, 분류)
│   ├── storyboard/   # 스토리보드 CRUD, Scene Builder
│   └── characters/   # 캐릭터 관리, LoRA 연동
├── models/           # SQLAlchemy ORM 26개 모델 (V3 Relational Schema)
├── templates/        # Jinja2 30개 템플릿 (스토리보드 5종 + Creative 21종 + 파셜 4종)
├── schemas.py        # Pydantic Request/Response 모델
├── config.py         # 환경변수/상수 SSOT
└── main.py           # FastAPI 앱 + Lifespan
```

### Frontend (`/frontend`)
```
frontend/
├── app/
│   ├── (app)/
│   │   ├── page.tsx       # Home (창작 대시보드)
│   │   ├── studio/        # Studio (씬 편집 워크스페이스)
│   │   ├── scripts/       # Scripts (Manual + AI Agent 대본 생성)
│   │   ├── storyboards/   # Storyboards (스토리보드 관리)
│   │   ├── characters/    # Characters (캐릭터 관리)
│   │   ├── library/       # Library (에셋 통합 관리)
│   │   ├── settings/      # Settings (프로젝트/시스템 설정)
│   │   └── ...            # voices, music, backgrounds, lab, pipeline-demo
│   ├── components/        # 공유 UI 컴포넌트 (20개 디렉토리)
│   ├── hooks/             # Custom Hooks (25개)
│   ├── store/             # Zustand 4-Store (Context/Storyboard/Render/UI)
│   └── utils/             # 유틸리티
├── tests/                 # Vitest 단위 테스트 + Playwright VRT/E2E
└── package.json
```

## Getting Started

### Prerequisites
1.  **Stable Diffusion WebUI**: `--api` 플래그 활성화
2.  **Google Gemini API Key**: `backend/.env` 설정
3.  **FFmpeg**: 시스템 설치
4.  **PostgreSQL**: DB 인스턴스

### Installation

**Audio Server (TTS & MusicGen):**
```bash
./run_audio.sh start
```

**Backend:**
```bash
cd backend
# .env 설정 (DATABASE_URL, GEMINI_API_KEY 등)
uv run main.py
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Testing

- **Backend**: `cd backend && uv run pytest` (1,902개 테스트)
- **Frontend**: `cd frontend && npm test` (352개 테스트)
- **VRT**: `cd frontend && npm run test:vrt`
- **총 2,254개 테스트**

## Documentation

### Product
- [Roadmap](docs/01_product/ROADMAP.md)
- [PRD](docs/01_product/PRD.md)
- [Feature Specs](docs/01_product/FEATURES/)

### Engineering
- [System Overview](docs/03_engineering/architecture/SYSTEM_OVERVIEW.md)
- [DB Schema](docs/03_engineering/architecture/DB_SCHEMA.md)
- [API Reference](docs/03_engineering/api/REST_API.md)
- [Test Cases](docs/03_engineering/testing/TEST_CASES.md)
- [Render Pipeline](docs/03_engineering/backend/RENDER_PIPELINE.md)

### Design & Operations
- [Design Guide](docs/02_design/STUDIO_DESIGN_GUIDE.md)
- [Deployment](docs/04_operations/DEPLOYMENT.md)
- [TTS Setup](docs/04_operations/TTS_SETUP.md)
- [SD WebUI Setup](docs/04_operations/SD_WEBUI_SETUP.md)
