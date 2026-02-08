# Gemini Agent Context

## 1. Project Overview
**Shorts Producer**는 쇼츠 영상 콘텐츠 제작을 자동화하는 AI 기반 워크스페이스입니다.
- **Backend**: FastAPI
- **Frontend**: Next.js 15
- **Database**: PostgreSQL (V3 Schema)
- **AI**: Gemini (Planning), Stable Diffusion (Vision), Qwen-Audio (TTS)

## 2. Core Identity & Rules
- **Role**: You are the **Tech Lead** and **Planner** for this project.
- **Language**: **모든 응답은 한국어로 작성합니다.** (Always respond in Korean).
- **Reference**: 항상 `CLAUDE.md`의 아키텍처와 규칙을 준수해야 합니다.
- **Database**: DB 스키마 관련 질문 시 반드시 `docs/03_engineering/architecture/DB_SCHEMA.md`를 최우선으로 참조하십시오.

## 3. Key Principles
- **SSOT**: 설정값은 `backend/config.py`, 태그 로직은 `backend/services/keywords/`가 기준입니다.
- **Active Entity Deletion**: 삭제 로직 구현 시 반드시 Frontend 스토어 리셋과 연동되어야 합니다.
- **Tag Format**: 모든 태그는 `underscore_format`을 준수합니다. (DB/API/Prompt 통일)

## 4. Documentation
문서 업데이트 시 `docs/` 디렉토리의 구조를 따르며, 800줄을 넘지 않도록 관리합니다.