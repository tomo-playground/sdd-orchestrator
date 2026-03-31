# SP-128: E2E CI 분리 — Fast(dev 서버) + Docker(빌드 검증)

- **branch**: feat/SP-128_e2e-fast-ci-split
- **priority**: P1
- **scope**: .github/workflows, frontend/e2e
- **assignee**: AI
- **created**: 2026-03-31

## 배경

현재 Docker E2E가 PR마다 10~28분 소요 → 자동 머지 블로킹.
self-hosted runner에 이미 dev 서버(backend:8000, frontend:3000)가 돌고 있어 Docker 빌드 불필요.

## 목표

PR gate는 dev 서버 대상 E2E(~10초), Docker E2E는 인프라 변경 시만.

## DoD (Definition of Done)

- [ ] `sdd-e2e-fast.yml` 신규: PR push → dev 서버 대상 Playwright (smoke + qa-patrol)
- [ ] `sdd-e2e.yml` 수정: Dockerfile/docker-compose 변경 시만 트리거 (paths 필터)
- [ ] 오케스트레이터 auto-merge 조건에서 Docker E2E 제외, fast E2E만 필수
- [ ] fast E2E 실패 시 머지 블로킹 유지

## 수정 대상 파일

- `.github/workflows/sdd-e2e-fast.yml` (신규)
- `.github/workflows/sdd-e2e.yml` (트리거 조건 변경)
- `sdd-orchestrator/src/sdd_orchestrator/tools/github.py` (CI 판정 로직)
