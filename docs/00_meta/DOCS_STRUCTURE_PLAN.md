# 문서 구조 개편 제안서 (v2)

기획, 디자인, 개발, 운영의 각 단계별로 스펙 문서를 정교하게 관리하기 위해, 아래와 같은 **단계별 번호 체계(Numbered Prefix)**를 제안합니다.

이 구조는 **"무엇을(기획)", "어떤 모습으로(디자인)", "어떻게(개발/운영)"** 만드는지를 명확히 구분하여, 프로젝트의 복잡도가 높아져도 문서를 쉽게 찾고 관리할 수 있도록 돕습니다.

## 📂 제안하는 디렉토리 구조

```text
docs/
├── 00_meta/                # 문서 관리 표준
│   ├── DOCS_GUIDE.md       # 문서 작성 가이드
│   └── CHANGELOG.md        # 전체 변경 이력
│
├── 01_product/             # [기획] 요구사항 및 전략 (Why & What)
│   ├── PRD.md              # 제품 요구사항 정의서 (기존 PRD.md 이동)
│   ├── ROADMAP.md          # 로드맵 및 마일스톤 (기존 ROADMAP.md 이동)
│   ├── FEATURES/           # 상세 기능 기획서 폴더
│   │   ├── prompt_system.md    # 프롬프트 시스템 기획
│   │   └── video_rendering.md  # 영상 렌더링 기능 기획
│   └── user_stories.md     # (선택) 사용자 시나리오
│
├── 02_design/              # [디자인] UX/UI 및 리소스 (Visual How)
│   ├── UI_SPECS.md         # UI 구조 및 레이아웃 정의 (ManagePage, Storyboard 등)
│   ├── ASSETS_GUIDE.md     # 이미지/영상 리소스 가이드
│   └── wireframes/         # (선택) Figma/스케치 이미지 저장
│
├── 03_engineering/         # [개발] 기술적 구현 명세 (Technical How)
│   ├── architecture/       # 시스템 설계
│   │   ├── SYSTEM_OVERVIEW.md  # [신규] 시스템 구성도, 데이터 흐름
│   │   └── DB_SCHEMA.md        # DB 스키마 및 관계도 (기존 파일 이동)
│   ├── api/                # 인터페이스 명세
│   │   └── REST_API.md     # API 엔드포인트 명세 (기존 API_SPEC.md 이동)
│   ├── backend/            # 백엔드 로직 명세
│   │   ├── PROMPT_PIPELINE.md  # 12-Layer 프롬프트 엔진 상세 (기존 파일 이동)
│   │   ├── RENDER_PIPELINE.md  # [신규] 영상 생성 및 FFmpeg 로직
│   │   └── CORE_SERVICES.md    # 기타 서비스 로직
│   └── frontend/           # 프론트엔드 아키텍처
│       ├── APP_STRUCTURE.md    # Next.js 라우팅 구조
│       └── STATE_MANAGEMENT.md # [신규] Zustand 및 상태 관리 패턴
│
├── 04_operations/          # [운영] 인프라 및 유지보수 (DevOps)
│   ├── DEPLOYMENT.md       # [신규] 배포 가이드, 환경 변수
│   ├── STORAGE_POLICY.md   # 스토리지 정리 및 관리 정책 (기존 ASSET_STORAGE.md 이동)
│   └── TROUBLESHOOTING.md  # 문제 해결 가이드
│
└── 99_archive/             # 보관소
    ├── archive/            # 기존 아카이브 폴더 이동
    └── ...
```

## 🚀 마이그레이션 계획 (Action Plan)

승인 시 다음 작업을 수행합니다:

1.  **폴더 생성**:
    -   `01_product`, `02_design`, `03_engineering`, `04_operations`, `00_meta` 등 상위 폴더 생성.
    -   `03_engineering` 하위에 `backend`, `frontend`, `api`, `architecture` 폴더 생성.
2.  **파일 이동 및 이름 변경**:
    -   `PRD.md`, `ROADMAP.md` → `01_product/` 로 이동
    -   `ui-redesign-proposal.md` → `02_design/UI_PROPOSAL.md` 로 이동 및 이름 변경
    -   `specs/DB_SCHEMA.md` → `03_engineering/architecture/DB_SCHEMA.md` 로 이동
    -   `specs/API_SPEC.md` → `03_engineering/api/REST_API.md` 로 이동 및 이름 변경
    -   `specs/PROMPT_PIPELINE_SPEC.md` → `03_engineering/backend/PROMPT_PIPELINE.md` 로 이동
    -   `specs/PROMPT_SPEC.md` → `03_engineering/backend/PROMPT_SPEC_V2.md` 로 이동
    -   `specs/ASSET_STORAGE_SPEC.md` → `04_operations/STORAGE_POLICY.md` 로 이동 및 이름 변경
    -   `docs/guides/SD_WEBUI_SETUP.md` → `04_operations/SD_WEBUI_SETUP.md` 로 이동
3.  **신규 필수 문서 템플릿 생성**:
    -   `03_engineering/backend/RENDER_PIPELINE.md` (렌더링 로직용 뼈대)
    -   `03_engineering/frontend/STATE_MANAGEMENT.md` (프론트 상태관리 뼈대)
