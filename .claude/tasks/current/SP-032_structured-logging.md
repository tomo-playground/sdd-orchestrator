---
id: SP-032
priority: P1
scope: backend
branch: feat/SP-032-structured-logging
created: 2026-03-21
status: pending
depends_on:
label: enhancement
assignee: stopper2008
---

## 무엇을
Backend 로깅 역할별 분리 — 단일 backend.log → 역할별 파일 분리 + 테스트 로그 격리

## 왜
- 서비스 로그와 테스트 로그가 같은 파일에 섞여서 분석 어려움
- 파이프라인 에러와 API 에러가 구분 안 됨
- Gemini API 호출 추적이 다른 로그에 묻힘
- 운영 시 문제 원인 추적 시간 증가

## 구현 범위

### 로그 파일 분리
```
logs/
├── backend.log      ← API 요청/응답, 서버 lifecycle
├── pipeline.log     ← LangGraph 노드 실행, 라우팅, 에러/fallback
├── gemini.log       ← Gemini API 호출/응답, token usage
└── test.log         ← pytest 실행 시만 사용 (서비스 로그와 격리)
```

### 구현 방법
- `logging.getLogger("backend.pipeline")`, `logging.getLogger("backend.gemini")` 등 계층 로거 사용
- 각 로거에 별도 FileHandler 설정
- `config.py`에서 SSOT 관리
- pytest 실행 시 `LOG_FILE=logs/test.log` 환경변수 또는 conftest에서 handler 교체

## 관련 파일
- `backend/config.py` — 로깅 설정 SSOT
- `backend/tests/conftest.py` — 테스트 로깅 설정
- `backend/services/agent/observability.py` — LangFuse + 파이프라인 로깅
- `backend/services/agent/nodes/*.py` — 노드별 logger 사용

## 완료 기준 (DoD)
- [ ] 역할별 로그 파일 분리 (backend, pipeline, gemini)
- [ ] pytest 실행 시 test.log로 격리
- [ ] 기존 logger 호출 변경 없이 동작 (하위 호환)
- [ ] 기존 테스트 통과
