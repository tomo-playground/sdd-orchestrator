# Shorts Factory - Actionable PRD (v3.1)

이 문서는 추상적인 전략이 아닌, **현재 개발 단계에서 구현 및 검증해야 할 실질적인 요구사항**을 정의합니다. 상세 아키텍처는 [System Overview](../03_engineering/architecture/SYSTEM_OVERVIEW.md)를 참조하세요.

## 1. 비즈니스 프로세스 맵 (Business Process Map)

전체 서비스가 사용자 입력으로부터 최종 영상으로 이어지는 비즈니스 프로세스입니다.

```mermaid
graph TD
    subgraph Planning ["1. 기획 단계"]
        Topic[주제/캐릭터 설정] --> Gemini[<b>Gemini API</b><br/>스토리보드 기획]
        Gemini --> Validation[<b>WD14 Tagger</b><br/>태그 정합성 검증]
        Validation --> DB_Store[<b>PostgreSQL</b><br/>데이터 저장]
    end

    subgraph Production ["2. 생산 단계"]
        DB_Store --> Prompt[V3 Prompt Engine]
        Prompt --> SD[<b>SD WebUI API</b><br/>이미지 생성]
        SD --> Quality[<b>Gemini Vision</b><br/>품질 및 일관성 검수]
        Quality -- "낮음 (Fail)" --> AutoEdit[Gemini Auto-Correction]
        AutoEdit --> SD
        Quality -- "높음 (Pass)" --> Audio[<b>Qwen3 TTS</b><br/>로컬 음성 생성]
    end

    subgraph Finalization ["3. 완성 단계"]
        Audio --> BGM[<b>Stable Audio Open</b><br/>AI BGM 생성]
        BGM --> FFmpeg[<b>FFmpeg Pipeline</b><br/>영상 합성]
        FFmpeg --> MinIO[<b>MinIO Storage</b><br/>객체 저장]
        MinIO --> History[활동 로그 및 대시보드 기록]
    end

    %% Data Connections
    DB_Store -.-> History
    SD -.-> Quality
```

---

## 2. 에셋 관리 및 데이터 영속화 (Assets & Persistence)

V3에서는 모든 에셋(이미지, 영상, 음성)이 고유 ID를 가지며 채택/기각 여부에 따라 생명 주기가 관리됩니다.

```mermaid
mindmap
    root((Asset Hub))
        Storage[Storage Mode]
            Local[Local: backend/outputs]
            S3[Cloud: MinIO/S3]
        Lifecycle[Lifecycle]
            Temporary[_build/*.tmp - 즉시 삭제]
            Cache[_prompt_cache - TTL 24h]
            Persistent[images/videos - 영구 보관]
        Metadata[Metadata DB]
            Project[Channel / Project]
            Activity[Action History]
            Evaluation[Quality Scores]
```

## 3. 제품 요구사항 및 우선순위

### 3.1 AI BGM 생성

**배경**: 현재 BGM은 정적 파일(File 모드)만 지원. 콘텐츠 분위기에 맞는 배경음악을 매번 수동으로 찾아야 하는 비효율 발생.

**요구사항**:

| # | 요구사항 | 우선순위 |
|---|---------|---------|
| 1 | Stable Audio Open 모델 기반 텍스트-투-뮤직 로컬 생성 (M4 Pro MPS) | P0 |
| 2 | Music Preset CRUD + 프롬프트 기반 미리듣기/생성 | P0 |
| 3 | 렌더 설정에서 BGM 모드 선택 (File: 기존 정적 파일 / AI: 프리셋 기반 생성) | P0 |
| 4 | 시스템 프리셋 10종 기본 제공 (Lo-fi Chill, Epic Cinematic, Dark Ambient 등) | P1 |
| 5 | SHA256 캐시로 동일 프롬프트 중복 생성 방지 | P1 |

**기능 명세**: [AI_BGM.md](../99_archive/features/AI_BGM.md)

*(기존 상세 내용 유지)*
...
