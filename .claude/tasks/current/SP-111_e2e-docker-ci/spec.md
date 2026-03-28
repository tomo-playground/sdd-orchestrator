# SP-111: Docker E2E 테스트 자동화 파이프라인

## 배경
PR에 test plan이 있어도 수동으로 검증하고 있음. PR별 격리된 Docker 환경에서 E2E 테스트를 자동 실행하여, 코드 리뷰 + E2E 검증 + 자동 수정까지 사람 개입 없이 돌아가는 파이프라인 구축.

## 목표
PR 열림 → test plan 감지 → Docker 환경 기동 → Claude가 Playwright 코드 생성/실행 → 실패 시 sdd-fix 자동 수정 → 통과 시 PR 코멘트

## DoD (Definition of Done)
- [ ] `docker-compose.e2e.yml` — E2E 전용 환경 (DB + Backend + Frontend + Playwright)
- [ ] 시드 데이터 스크립트 — 테스트 전제조건용 DB 초기 데이터
- [ ] Backend Dockerfile — API 서버 컨테이너화
- [ ] Frontend Dockerfile — Next.js 빌드 + 서빙
- [ ] `sdd-e2e.yml` GitHub Actions 워크플로우 — PR 트리거, test plan 감지, Docker 환경 기동/파기
- [ ] Claude가 test plan → Playwright 테스트 코드 자동 생성
- [ ] 테스트 결과 PR 코멘트 (통과/실패 + 스크린샷/트레이스)
- [ ] 실패 시 sdd-fix 연동 (자동 수정 → 재실행, 최대 3회)
- [ ] 개발 환경에 영향 zero 확인

## 아키텍처

```
[PR opened/synchronize]
  │
  ├─ sdd-review.yml (병렬 — 코드 리뷰)
  │
  └─ sdd-e2e.yml (병렬 — E2E 테스트)
       │
       ├─ test plan 파싱 (PR body에서 "## Test plan" 추출)
       │
       ├─ docker compose -f docker-compose.e2e.yml up
       │   ├─ e2e-db (PostgreSQL + 시드 데이터)
       │   ├─ e2e-backend (PR 브랜치 코드)
       │   └─ e2e-frontend (PR 브랜치 빌드)
       │
       ├─ Claude가 test plan → Playwright 스크립트 생성
       │
       ├─ Playwright 실행 (headless)
       │   ├─ 통과 → PR 코멘트 ✅
       │   └─ 실패 → 스크린샷/트레이스 첨부 + sdd-fix 트리거
       │
       └─ docker compose down (환경 파기)
```

## Docker 구성

```yaml
# docker-compose.e2e.yml
services:
  e2e-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: shorts_e2e
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    volumes:
      - ./scripts/e2e-seed.sql:/docker-entrypoint-initdb.d/seed.sql
    healthcheck:
      test: pg_isready -U test -d shorts_e2e

  e2e-backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.e2e
    depends_on:
      e2e-db: { condition: service_healthy }
    environment:
      DATABASE_URL: postgresql://test:test@e2e-db:5432/shorts_e2e
    ports: ["18000:8000"]

  e2e-frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.e2e
    depends_on: [e2e-backend]
    environment:
      NEXT_PUBLIC_API_URL: http://e2e-backend:8000/api/v1
    ports: ["13000:3000"]

  e2e-runner:
    image: mcr.microsoft.com/playwright:v1.58.0
    depends_on: [e2e-frontend]
    volumes:
      - ./frontend/e2e:/e2e
      - /tmp/e2e-results:/results
```

## 호스트 자원
- CPU: Ryzen 9 9950X3D 24코어 — 여유 충분
- RAM: 39GB (16GB 가용) — E2E 환경 ≈ 2~3GB
- Disk: 756GB 여유
- Docker: 이미 9개 컨테이너 운영 중

## 시드 데이터 요건
- Project 1개, Group 1개
- Character 2개 (speaker A/B)
- StyleProfile 2개
- VoicePreset 2개
- Storyboard 1개 (씬 3개 포함)
- LoRA 1개

## 스코프 제외
- GPU 의존 테스트 (이미지 생성, TTS) — mock API로 대체
- VRT (별도 파이프라인)
- 성능 테스트

## 우선순위
P0 — 즉시 착수
