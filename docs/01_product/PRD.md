# Shorts Factory - Actionable PRD (v3.1)

이 문서는 추상적인 전략이 아닌, **현재 개발 단계에서 구현 및 검증해야 할 실질적인 요구사항**을 정의합니다.

## 1. 비즈니스 프로세스 맵 (Business Process Map)

전체 서비스가 사용자 입력으로부터 최종 영상으로 이어지는 비즈니스 프로세스입니다.

```mermaid
graph TD
    subgraph Planning ["1. 기획 단계"]
        Topic[주제/캐릭터 설정] --> Gemini[Gemini Storyboard 생성]
        Gemini --> Validation[Danbooru 태그 검증]
        Validation --> DB_Store[<b>DB 저장</b><br/>Storyboards, Scenes]
    end

    subgraph Production ["2. 생산 단계"]
        DB_Store --> Prompt[V3 Prompt Engine]
        Prompt --> SD[Stable Diffusion 생성]
        SD --> Quality[WD14/Vision 품질 검수]
        Quality -- "낮음" --> AutoEdit[Gemini Auto-Correction]
        AutoEdit --> SD
        Quality -- "높음" --> Audio[Qwen3 TTS 생성]
    end

    subgraph Finalization ["3. 완성 단계"]
        Audio --> FFmpeg[Render Pipeline 렌더링]
        FFmpeg --> Asset[<b>최종 결과물</b><br/>MP4, Thumbnail]
        Asset --> History[히스토리 및 로그 기록]
    end

    %% Data Connections
    DB_Store -.-> History
    SD -.-> Quality
```

## 2. 데이터 영속화 구조 (Persistence Hierarchy)

V3 아키텍처의 핵심 계층 구조입니다.

```mermaid
mindmap
    root((Shorts Producer))
        Project[Project : 채널 단위]
            Group[Group : 시리즈/주제 단위]
                Storyboard[Storyboard : 영상 단위]
                    Scene[Scene : 장면 단위]
                        CharacterAction[Character Action]
                        SceneTag[Scene Tags]
                    Asset[Media Asset : 이미지/영상]
                    History[Activity Log]
```

---

## 3. 프로젝트 범위 (Scope & Priorities)
*(기존 상세 내용 유지)*
...
