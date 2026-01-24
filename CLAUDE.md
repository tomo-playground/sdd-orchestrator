# 프로젝트: Shorts Producer

## 개요
`shorts-producer`는 AI 기반 쇼츠 영상 자동화 워크스페이스입니다. Google Gemini (스토리보드/검증), Stable Diffusion (이미지 생성), FFmpeg (렌더링)을 조합하여 텍스트 주제를 완성된 영상으로 변환합니다.

## 아키텍처

### 1. Backend (`/backend`)
**FastAPI** 기반. 리팩토링 완료 (모듈화).

**디렉토리 구조**:
```
backend/
├── main.py              # FastAPI 앱 진입점 (라우터 등록)
├── config.py            # 설정, 상수, 전역 객체
├── schemas.py           # Pydantic 모델
├── routers/             # API 엔드포인트
│   ├── storyboard.py    # 스토리보드 생성
│   ├── images.py        # 이미지 생성/검증
│   ├── render.py        # 비디오 렌더링
│   ├── presets.py       # 프리셋 관리
│   └── cleanup.py       # 스토리지 정리
├── services/            # 비즈니스 로직
│   ├── video.py         # VideoBuilder 클래스
│   ├── rendering.py     # 오버레이, 자막 렌더링
│   ├── validation.py    # WD14, Gemini 검증
│   ├── prompt.py        # 프롬프트 처리
│   ├── image.py         # 이미지 유틸리티
│   ├── avatar.py        # 아바타 생성
│   ├── keywords.py      # 키워드 관리
│   ├── presets.py       # 프리셋 로직
│   ├── cleanup.py       # 정리 로직
│   └── utils.py         # 공통 유틸리티
├── templates/           # Jinja2 스토리보드 템플릿
├── constants/           # 레이아웃 상수
└── assets/              # 폰트, 오버레이, 오디오
```

**핵심 기능**:
- **Storyboarder**: Gemini + Jinja2로 스크립트/프롬프트 생성
- **Image Pipeline**: SD WebUI API + WD14/Gemini 검증 루프
- **Renderer**: FFmpeg (자막, 오버레이, Audio Ducking)

### 2. Frontend (`/frontend`)
**Next.js 14+ (App Router)** + **Tailwind CSS**.

**디렉토리 구조**:
```
frontend/app/
├── page.tsx             # 메인 스튜디오 (1,800줄)
├── components/          # UI 컴포넌트 (20+개)
│   ├── StoryboardGeneratorPanel.tsx
│   ├── PromptSetupPanel.tsx
│   ├── SceneCard.tsx
│   ├── RenderSettingsPanel.tsx
│   └── ...
├── hooks/               # 커스텀 훅
│   ├── useAutopilot.ts  # Autopilot 상태 머신
│   └── useDraftPersistence.ts
├── types/               # TypeScript 타입
├── constants/           # 상수 정의
└── utils/               # 유틸리티 함수
```

**핵심 기능**:
- **Autopilot**: 스토리보드 → 이미지 생성 → 검증 → 렌더링 자동화
- **Resume/Checkpoint**: 중단된 작업 이어하기
- **Draft Persistence**: 새로고침 후 복구

## 현재 상태 (Phase 5 완료)

### 완료된 기능
- [x] Backend 리팩토링 (`logic.py` 2,300줄 → 279줄, 88% 감소)
- [x] Frontend 리팩토링 (`page.tsx` 4,222줄 → 1,832줄, 57% 감소)
- [x] VRT (Visual Regression Test) 36/36 통과
- [x] Storage Cleanup API
- [x] Preset System (9개 프리셋)
- [x] Pixel-based Subtitle Wrapping
- [x] Audio Ducking (sidechaincompress)
- [x] Resume/Checkpoint 기능

### 진행 중 (Phase 6)
- [ ] Character System (다중 캐릭터)
- [ ] Prompt Builder (태그 선택 UI)
- [ ] keywords.json → SQLite 마이그레이션

## 규칙 및 가이드라인

### 문서 참조
- **우선순위**: `docs/ROADMAP.md` (작업은 여기서 선택)
- **스펙**: `docs/PRD.md`
- **API**: `docs/API_SPEC.md`

### 코드 크기 가이드라인
| 단위 | 권장 | 최대 | 초과 시 조치 |
|------|------|------|-------------|
| **함수/메서드** | 30줄 | 50줄 | 헬퍼 함수로 분리 |
| **클래스/컴포넌트** | 150줄 | 200줄 | 책임 분리 검토 |
| **파일** | 300줄 | 400줄 | 모듈 분리 |

**원칙**:
- 한 함수는 **한 가지 일**만 수행 (Single Responsibility)
- 중첩(nesting)은 **3단계 이하** 유지
- 매개변수는 **4개 이하** 권장 (초과 시 객체로 묶기)

## 사전 요구사항
- **Stable Diffusion WebUI**: `http://127.0.0.1:7860` (`--api` 옵션으로 실행)
- **환경 변수**: `backend/.env`에 `GEMINI_API_KEY` 필수
