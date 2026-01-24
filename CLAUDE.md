# 프로젝트: Shorts Producer

AI 기반 쇼츠 영상 자동화 워크스페이스. Gemini (스토리보드) + Stable Diffusion (이미지) + FFmpeg (렌더링).

## 아키텍처

| 레이어 | 기술 | 핵심 |
|--------|------|------|
| Backend | FastAPI | `routers/` (API), `services/` (로직) |
| Frontend | Next.js 14 | `app/page.tsx` (스튜디오), `hooks/useAutopilot.ts` |

## 문서 참조
- **작업 선택**: `docs/ROADMAP.md`
- **제품 스펙**: `docs/PRD.md`
- **API 명세**: `docs/API_SPEC.md`
- **개발 가이드**: `docs/CONTRIBUTING.md`

## 코드 크기 가이드라인
| 단위 | 권장 | 최대 |
|------|------|------|
| 함수/메서드 | 30줄 | 50줄 |
| 클래스/컴포넌트 | 150줄 | 200줄 |
| 파일 | 300줄 | 400줄 |

**원칙**: Single Responsibility, 중첩 3단계 이하, 매개변수 4개 이하

## 사전 요구사항
- **SD WebUI**: `http://127.0.0.1:7860` (`--api` 옵션)
- **환경 변수**: `backend/.env`에 `GEMINI_API_KEY`

## Sub Agents

| Agent | 역할 | Commands |
|-------|------|----------|
| **PM Agent** | 로드맵/우선순위/문서 관리 | `/roadmap`, `/vrt` |
| **Prompt Engineer** | SD 프롬프트 최적화 | `/prompt-validate`, `/sd-status` |
| **Storyboard Writer** | 스토리보드/스크립트 작성 | `/roadmap` |
| **QA Validator** | 품질 체크/TROUBLESHOOTING 관리 | `/vrt`, `/sd-status`, `/prompt-validate` |
| **FFmpeg Expert** | 렌더링/비디오 효과 | `/vrt`, `/roadmap` |

## Commands

| Command | 역할 |
|---------|------|
| `/roadmap` | 로드맵 조회/업데이트 |
| `/vrt` | Visual Regression Test 실행 |
| `/sd-status` | SD WebUI 상태 확인 |
| `/prompt-validate` | 프롬프트 문법 검증 |

> Agents/Commands 관리 규칙은 `docs/CONTRIBUTING.md` 참조
