---
id: SP-109
priority: P1
scope: orchestrator
branch: feat/SP-109-orch-config-plugin
created: 2026-03-28
depends_on: SP-108
label: refactor
---

## 무엇을 (What)
오케스트레이터 config.py에서 프로젝트 전용 값을 plugin/config 주입 방식으로 분리.

## 왜 (Why)
현재 `orchestrator/config.py`에 shorts-producer 전용 값이 하드코딩:
- Sentry 프로젝트명 (`shorts-producer-backend` 등)
- GitHub repo (`tomo-playground/shorts-producer`)
- LLM 시스템 프롬프트 (SDD 워크플로우 설명)
- 태스크 경로 (`.claude/tasks/`)

범용 패키지 분리의 전제 조건. 프로젝트별 설정은 `sdd.config.yaml` 또는 환경변수로 주입.

## 완료 기준 (DoD)

### Must (P0)
- [ ] 프로젝트 전용 상수를 `ProjectConfig` dataclass로 추출
- [ ] `sdd.config.yaml` (또는 `.sdd/config.yaml`) 로드 로직 추가
- [ ] config 미존재 시 기존 기본값으로 fallback (하위 호환)
- [ ] Sentry 프로젝트명, GitHub repo, 태스크 경로가 config에서 주입

### Should (P1)
- [ ] LLM 시스템 프롬프트를 외부 파일로 분리 (현재 config.py 인라인)
- [ ] `MAX_PARALLEL_RUNS`, `CYCLE_INTERVAL` 등 운영 파라미터도 config로 이동
