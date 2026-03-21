---
id: SP-037
priority: P1
scope: infra
branch: feat/SP-037-server-operational-hardening
created: 2026-03-21
status: pending
depends_on:
label: enhancement
assignee: stopper2008
---

## 무엇을
서버 운영 안정성 강화 — uvicorn, health-check, cron GC

## 왜
Tech Lead 전수조사 WARNING 항목 통합:
- W-3: uvicorn timeout-keep-alive 미설정 → SSE 끊김
- W-5: Checkpoint GC 자동화 없음 → DB 무한 증가
- W-6: Health Check에 SD WebUI 누락
- W-7: CI workflow timeout 미설정
- W-8: Health Check concurrency 미설정
- Media Asset temp 자동 정리 없음

## 수정 범위
1. `run_backend.sh`: `--timeout-keep-alive 120` 추가
2. `.github/workflows/health-check.yml`: SD WebUI 체크 + concurrency 추가
3. `.github/workflows/ci.yml`: `timeout-minutes: 20` 추가
4. Checkpoint GC 주간 cron 추가
5. Media Asset temp 정리 일간 cron 추가

## 완료 기준 (DoD)
- [ ] uvicorn keep-alive timeout 설정
- [ ] SD WebUI 헬스체크 추가
- [ ] CI/Health Check timeout + concurrency 설정
- [ ] Checkpoint GC cron 등록
- [ ] Media temp 정리 cron 등록
