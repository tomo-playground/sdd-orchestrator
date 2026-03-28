---
id: SP-110
priority: P2
scope: orchestrator
branch: feat/SP-110-orch-package-separation
created: 2026-03-28
status: done
approved_at: 2026-03-28
depends_on: SP-108, SP-109
label: feature
---

## 무엇을 (What)
오케스트레이터를 독립 Python 패키지로 분리 — `sdd-orchestrator`.

## 왜 (Why)
shorts-producer 인큐베이팅 완료 후, 신규 프로젝트에 `pip install sdd-orchestrator`로 SDD 자율 실행을 즉시 적용하기 위함.

## 완료 기준 (DoD)

### Must (P0)
- [ ] 별도 Git 리포지토리 생성 (`tomo-playground/sdd-orchestrator`)
- [ ] `pyproject.toml` + `pip install -e .` 가능한 패키지 구조
- [ ] shorts-producer에서 `orchestrator/` 제거, 패키지 의존으로 전환
- [ ] `sdd init` CLI 명령어 — 프로젝트에 `.sdd/config.yaml` + 기본 스킬 생성
- [ ] 기존 테스트 전부 통과

### Should (P1)
- [ ] README + 퀵스타트 문서
- [ ] GitHub Actions 템플릿 (`sdd-sync.yml`, `health-check.yml`) 자동 생성
- [ ] `.claude/agents/`, `.claude/skills/` 템플릿 포함

### Could (P2)
- [ ] npm wrapper (`npx @tomo/sdd-kit init`)
- [ ] 프로젝트 타입별 프리셋 (FastAPI+Next.js, Django, etc.)
