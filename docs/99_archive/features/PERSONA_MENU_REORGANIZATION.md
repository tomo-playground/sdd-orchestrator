# Phase 21: Persona-based Menu Reorganization

**상태**: 완료 (2026-02-28)

## 목표

Admin 메뉴를 Creator/Developer 페르소나 기준으로 3-tier로 재편성.

## 페르소나 정의

| 페르소나 | 역할 | 메뉴 영역 |
|---------|------|----------|
| Creator (일반 유저) | 에셋 생성 + 영상 제작 | Home, Studio, Library, Settings |
| Developer (도구 개발자) | 태그·SD·프롬프트 엔진 튜닝 | Dev |

## 최종 구조

```
상단 내비: Home | Studio | Library | Settings | --- | Dev

Library /library
├── Characters  (캐릭터 CRUD + Builder)
├── Styles      (Style Profile CRUD)
├── Voices      (음성 프리셋 CRUD)
├── Music       (음악 프리셋 CRUD)
└── Prompts     (프롬프트 히스토리)

Settings /settings
├── Render Presets  (렌더 프리셋 CRUD)
├── YouTube         (채널 연결)
└── Trash           (삭제 콘텐츠 복구)

Dev /dev
├── Tags     (태그 분류/승인/통계)
├── Lab      (Tag Lab, Scene Lab, Analytics, Tag Browser)
├── Logs     (Activity Logs, Gemini Edit Analytics)
├── SD Models (Checkpoints, Embeddings, Civitai, LoRA)
└── System   (캐시, Media GC, Gemini 설정, Memory)
```

## 구현 내역

| 서브태스크 | 내용 | 상태 |
|-----------|------|------|
| 21-1 | Shell 컴포넌트 + Route Layout | ✅ |
| 21-2 | Library 페이지 이동 | ✅ |
| 21-3 | Styles 분리 (Library + Dev/SD Models) | ✅ |
| 21-4 | Settings 페이지 생성 | ✅ |
| 21-5 | Dev 페이지 이동 | ✅ |
| 21-6 | 네비게이션 링크 + Dead code 정리 | ✅ |

## 주요 컴포넌트

- `LibraryShell.tsx` — 탭 기반 (Characters|Styles|Voices|Music|Prompts)
- `SettingsShell.tsx` — 탭 기반 (Render Presets|YouTube|Trash)
- `DevShell.tsx` + `DevSidebar.tsx` — 사이드바 기반 (3그룹: Prompt/Quality/Infra)

## 후방 호환

모든 `/admin/*` 경로는 새 경로로 redirect 유지.
