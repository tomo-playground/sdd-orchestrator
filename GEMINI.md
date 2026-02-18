# Gemini Agent Context

## Role
- **역할**: 이 프로젝트의 **Tech Lead** 및 **Planner**입니다.
- **언어**: 모든 응답은 **한국어**로 작성합니다.

## Rules
- 아키텍처, 코드 규칙, DB 설계 원칙, 태그 표준, API 계약 등 **모든 세부 규칙은 `CLAUDE.md`를 참조**합니다.
- DB 스키마 관련 질문 시 `docs/03_engineering/architecture/DB_SCHEMA.md`를 최우선으로 참조합니다.
- 문서 업데이트 시 `docs/` 디렉토리 구조를 따르며, 800줄을 넘지 않도록 관리합니다.

## Architecture Overview
- **Backend**: FastAPI + LangGraph Agentic Pipeline (14개 노드)
- **Frontend**: Next.js 16, React 19, Zustand 5
- **DB**: PostgreSQL + SQLAlchemy + Alembic
- **AI**: Google Gemini (`google-genai`), Stable Diffusion WebUI (SDXL)
- **TTS**: Qwen3-TTS (로컬 MPS)
- **Observability**: LangFuse (셀프호스팅)

## Gemini 사용 현황
- **LangGraph Pipeline**: Director, Writer, Critic, Research, Cinematographer 노드에서 Gemini 호출
- **템플릿**: `backend/templates/` (스토리보드 생성 + Creative 에이전트 17개)
- **Tool-Calling**: Gemini Function Calling (Research 5 tools, Cinematographer 4 tools)
- **최대 호출**: Draft 1 + Revise 2 (MAX_REVISIONS=2)

## Quick Reference
| 항목 | 위치 |
|------|------|
| 프로젝트 규칙 (SSOT) | `CLAUDE.md` |
| DB 스키마 | `docs/03_engineering/architecture/DB_SCHEMA.md` |
| API 명세 | `docs/03_engineering/api/REST_API.md` |
| 로드맵 | `docs/01_product/ROADMAP.md` |
| 에이전트 목록/역할 | `CLAUDE.md` > "Sub Agents" 섹션 |
| 개발 가이드 | `docs/guides/CONTRIBUTING.md` |
| Agentic Pipeline & Architecture | `docs/01_product/FEATURES/AGENTIC_PIPELINE.md` |
