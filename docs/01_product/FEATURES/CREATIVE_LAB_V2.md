# Creative Lab V2: Shorts Multi-Agent Scenario Generator

**Phase**: 7-1 #24
**상태**: Phase 3 구현 완료 (Multi-Character + Sound Designer + Copyright Reviewer)
**우선순위**: P0

## 배경

쇼츠 플랫폼(30-60초 영상)의 전체 파이프라인:
Topic → Storyboard(Gemini) → Scene Edit → SD Image → TTS → FFmpeg Render → YouTube

Creative Lab V1은 자유형식 마크다운 debate로, 이 파이프라인과 연결되지 않는다.
V2는 **에이전트가 실제 쇼츠 시나리오를 만들고**, Studio로 바로 보낼 수 있게 한다.

핵심 설계 원칙:
- **에이전트 간 모든 소통을 트레이싱** → 타임라인 UI로 시각화
- **리더 에이전트의 이중 역할**: 자율 결정 + 사용자 판단 지원
- 창의성(debate)과 전문가 협업(pipeline) 2단계 분리
- 기존 Structure(Monologue/Dialogue/Narrated Dialogue) 재사용

## 선행 조건

| 항목 | 이유 |
|------|------|
| 7-1 #7 (Structure별 전용 Gemini 템플릿 5종) | Scriptwriter가 Structure별 speaker 규칙을 주입하려면 템플릿 시스템 필수 |

---

## 1. 에이전트 설계

### 에이전트 로스터 (9명)

```
┌─────────────────────────────────────────────────────────────────┐
│                    ┌──────────────────┐                          │
│                    │  Creative        │  총괄 리더               │
│                    │  Director (리더) │  자율 결정 + 사용자 지원   │
│                    └────────┬─────────┘                          │
│            ┌────────────────┼────────────────┐                  │
│     ┌──────┴──────┐ ┌──────┴──────┐ ┌───────┴─────┐           │
│     │ Architect   │ │ Architect   │ │ Architect   │  Phase 1   │
│     │ "감정 아크" │ │ "비주얼 훅" │ │ "반전 구조" │  콘셉트    │
│     └─────────────┘ └─────────────┘ └─────────────┘            │
│                    ┌──────────────────┐                          │
│                    │ Devil's Advocate │  Phase 1 비판적 검증      │
│                    └──────────────────┘                          │
│     ┌─────────────┐                                            │
│     │ Reference   │  Phase 0 소재 수집 (Future)                  │
│     │ Analyst     │                                              │
│     └─────────────┘                                             │
│     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│     │ Scriptwriter│ │ Cinemato-   │ │ Sound       │  Phase 2   │
│     │ "대본 전문" │ │ grapher     │ │ Designer    │  전문가    │
│     └─────────────┘ └─────────────┘ └─────────────┘            │
│                      ┌─────────────┐                            │
│                      │ Copyright   │  Phase 2 저작권 검증        │
│                      │ Reviewer    │                             │
│                      └─────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

| # | 에이전트 | Phase | 역할 | 구현 |
|---|----------|-------|------|------|
| 1 | **Creative Director** | 1+2 | 총괄, 평가, QC, 라우팅. Auto/Advisor 이중 모드 | O (Advisor만) |
| 2 | **Story Architect (Emotional Arc)** | 1 | 감정 곡선 중심 콘셉트 (hook 0.2, arc 0.4, feasibility 0.2, originality 0.2) | O |
| 3 | **Story Architect (Visual Hook)** | 1 | 시각적 훅 중심 콘셉트 (hook 0.4, arc 0.2, feasibility 0.2, originality 0.2) | O |
| 4 | **Story Architect (Narrative Twist)** | 1 | 서사 반전 중심 콘셉트 (hook 0.2, arc 0.2, feasibility 0.2, originality 0.4) | O |
| 5 | **Devil's Advocate** | 1 | 5관점 비판적 검증 | O |
| 6 | **Reference Analyst** | 0 | 레퍼런스 구조/훅/감정/페이싱 인사이트 추출 | X (Future) |
| 7 | **Scriptwriter** | 2 | 2-Pass 스크립트 (Draft → Self-Edit) + Multi-Character 지원 | O |
| 8 | **Cinematographer** | 2 | Danbooru 태그 비주얼 설계 + speaker별 캐릭터 태그 | O |
| 9 | **Sound Designer** | 2 | BGM 방향 추천 (Stable Audio Open 프롬프트) | O |
| 10 | **Copyright Reviewer** | 2 | 4관점 저작권/독창성 검증 | O |

### Creative Director — 이중 모드 설계

```
┌─ Mode A: Auto-pilot (자율 결정) ──────────────────────────────┐
│  • 콘셉트 점수 차이 > 0.15 → 자동 선택                         │
│  • 파이프라인 Step 완료 → 자동으로 다음 Step 전달               │
│  • QC 경미한 이슈 → 자동 피드백 + 재실행                       │
│  • 모든 결정은 trace에 기록 (사후 리뷰 가능)                    │
└───────────────────────────────────────────────────────────────┘
┌─ Mode B: Advisor (사용자 판단 지원) ──────────────────────────┐
│  • 콘셉트 비교표 제시 (장단점, 점수 근거)                       │
│  • 추천안 + 이유 명시 ("A 추천: 감정곡선이 30초에 적합")        │
│  • QC 이슈 → 수정안 제시 + 사용자 선택                         │
└───────────────────────────────────────────────────────────────┘
전환 로직:
• 사용자가 Setup에서 모드 선택 (기본: Advisor)
• Auto-pilot 중에도 확신도 낮으면 자동 Advisor 전환
• 임계값: score_gap < 0.15 or QC critical → Advisor
```

### 콘셉트 출력 스키마 (Architect)

```json
{
  "title": "실수 속 성장",
  "hook": "떨리는 손으로 칼을 잡는 클로즈업",
  "hook_strength": "visual_tension",
  "arc": "도전 → 실패 → 재도전 → 성공",
  "key_moments": [
    { "beat": "opening", "description": "첫 칼질에 긴장하는 표정", "camera_hint": "close-up" },
    { "beat": "turning_point", "description": "양파 때문에 눈물", "camera_hint": "close-up" },
    { "beat": "low_point", "description": "불 세기 조절 실패", "camera_hint": "cowboy_shot" },
    { "beat": "climax", "description": "웃으며 완성", "camera_hint": "full_body" }
  ],
  "mood_progression": "tense → frustrated → determined → joyful",
  "estimated_scenes": 12,
  "pacing_note": "실패 장면은 빠르게, 성공은 여유있게"
}
```

### Devil's Advocate — 5관점

| 관점 | 분석 내용 | 예시 |
|------|----------|------|
| 훅 강도 | 첫 3초 안에 시청자를 잡을 수 있는가? | "오프닝이 평범한 상황 설명. 시각적 긴장 부재" |
| 30초 적합성 | 이 구조가 30초 안에 전달 가능한가? | "4단계 아크는 30초에 과밀. 3단계로 축소 필요" |
| 감정 진정성 | 감정 곡선이 인위적이지 않은가? | "갑작스러운 감동 전환. 중간 계기 부족" |
| 시각 실현 | SD로 생성 가능한 장면인가? | "비 오는 밤 기차역 — 환경 조합 난이도 높음" |
| 독창성 | 기존 바이럴 콘텐츠와 차별화 되는가? | "요리 도전 → 실패 → 성공은 이미 포화된 구조" |

### Scriptwriter — 2-Pass 접근법

```
Pass 1 — Draft: 콘셉트 → 씬 분할 + 대사 작성 + duration 배정
Pass 2 — Self-Edit (단일 LLM 호출 내):
  ① TTS 자연스러움: 어미/접속사 교정
  ② 감정 곡선 정합: mood_progression과 대사 톤 일치
  ③ 중복 제거: 연속 씬 유사 표현 방지
  ④ 훅 강화: 첫 1-2씬 대사 흡인력 재검토
  ⑤ 페이싱 미세조정: 대사 길이에 따른 duration 재계산
```

---

## 2. 파이프라인 전체 흐름

### 피드백 루프 원칙

- Phase 1: 사용자 설정 라운드 수 (기본 2, 최대 5). 조기 수렴: best > 0.85 AND gap > 0.2
- Phase 2: 각 Step 최대 2회 재실행 (MAX_RETRIES = 2). 실패 시 현재 결과로 진행

```
══════ Phase 1: 콘셉트 Debate (멀티라운드) ══════

  ┌─── Round 1 ──────────────────────────────────────────────────┐
  │  Director instruction (초기 지시)                              │
  │           ▼                                                   │
  │  ┌────────────┐ ┌────────────┐ ┌────────────┐  ② 병렬 생성   │
  │  │ Emotional  │ │ Visual     │ │ Narrative  │               │
  │  │ Arc        │ │ Hook       │ │ Twist      │               │
  │  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘               │
  │        └───────────────┼──────────────┘                      │
  │                        ▼                                     │
  │             Devil's Advocate ③ 비판적 분석                    │
  │                        ▼                                     │
  │             Director ④ evaluate (비판 + 점수 종합)            │
  └──────────────────────────────────────────────────────────────┘
                      │ (Round N 또는 조기 수렴)
                      ▼
             Director decision (Advisor: 비교표 제시)
                      │ 사용자 선택 → 콘셉트 확정
                      ▼

══════ Phase 2: 전문가 Pipeline (순차) ══════

  Director handoff → Scriptwriter
                        │ ⑥ 2-Pass 스크립트 생성 (Multi-Character 지원)
                        ▼
                   Director QC 검증
                   PASS │ FAIL → feedback (max 2회)
                        ▼
  Director handoff → Cinematographer
                        │ ⑧ Danbooru 태그 비주얼 설계 (speaker별 캐릭터 태그)
                        ▼
                   Director QC 검증
                   PASS │ FAIL → feedback (max 2회)
                        ▼
  Director handoff → Sound Designer
                        │ ⑩ BGM 방향 추천 (SAO 프롬프트)
                        ▼
                   Director QC 검증
                   PASS │ FAIL → feedback (max 2회)
                        ▼
  Director handoff → Copyright Reviewer
                        │ ⑫ 4관점 저작권/독창성 검증
                        ▼
                   Director QC 검증
                   PASS │ FAIL → feedback (max 2회)
                        ▼
                  ✅ 완성! [Send to Studio]
```

---

## 3. 트레이싱 시스템

### trace_type 전체 목록

| trace_type | 발생 시점 | from (agent_role) | to (target_agent) | 내용 |
|------------|----------|-------------------|-------------------|------|
| `instruction` | 라운드 시작 | Director | 전체/특정 에이전트 | 작업 지시 + 맥락 |
| `generation` | LLM 호출 | 에이전트 | NULL | 콘셉트/스크립트/비주얼 결과물 |
| `evaluation` | Phase 1 평가 | Director | NULL (self) | 점수, 피드백, 라운드 요약 |
| `decision` | 의사결정 | Director | 사용자/self | 선택 + 근거 + 대안 |
| `handoff` | Phase 2 전환 | Director | 다음 에이전트 | 이전 결과물 + 지시 |
| `feedback` | 품질 미달 | Director | 해당 에이전트 | 문제점 + 개선 방향 |
| `quality_report` | QC 수행 | Director | NULL (self) | 자동검증 결과 |

### decision_context 스키마

```json
{
  "mode": "auto | advisor",
  "options": [
    { "label": "Concept A", "score": 0.85, "pros": ["..."], "cons": ["..."] }
  ],
  "selected": "Concept A",
  "reason": "감정곡선이 명확하고 30초 내 전달 가능",
  "confidence": 0.85,
  "escalated_to_user": false
}
```

### 트레이싱 흐름 예시

```
Session #42 — "요리를 처음 배우는 소녀" (30s, Monologue, Korean)

═══ Phase 1: 콘셉트 Debate ═══
#1  instruction   Director → [All Architects]     0 tokens (system)
#2  generation    Emotional Arc → Director         1.2K tok  3.2s
#3  generation    Visual Hook → Director           1.1K tok  3.0s
#4  generation    Narrative Twist → Director        1.2K tok  3.1s
#5  evaluation    Director → (self)                scores: {emotional: 0.85, visual: 0.72}
#6  decision      Director → User (advisor, gap=0.13 < 0.15)

═══ Phase 2: 전문가 Pipeline ═══
#7  handoff       Director → Scriptwriter
#8  generation    Scriptwriter → Director          2.1K tok  4.5s
#9  quality_report Director (PASS)
#10 handoff       Director → Cinematographer
#11 generation    Cinematographer → Director        3.2K tok  6.1s
#12 quality_report Director (WARN: Scene 4 tag)
#13 feedback      Director → Cinematographer       "Scene 4: room → bedroom"
#14 generation    Cinematographer (재실행)           0.8K tok  2.1s
#15 quality_report Director (PASS)
#16 handoff       Director → Sound Designer
#17 generation    Sound Designer → Director         0.6K tok  2.0s
#18 quality_report Director (PASS)
#19 handoff       Director → Copyright Reviewer
#20 generation    Copyright Reviewer → Director     0.9K tok  2.5s
#21 quality_report Director (PASS)
#22 decision      Director (auto: "모든 QC 통과")
```

---

## 4. 타임라인 UI

### 메인 타임라인 뷰

```
┌─────────────────────────────────────────────────────────────────┐
│  Session #42 — 요리를 처음 배우는 소녀       Status: completed   │
│  30s • Monologue • Korean • Character: 하루                     │
├─────────────────────────────────────────────────────────────────┤
│  Filter: [All ▼]  Director | Architects | Scriptwriter | Cine. │
│                                                                 │
│  ── Phase 1: 콘셉트 Debate ─────────────────────────────────── │
│  ┌ 10:00:00 ─────────────────────────────────────────────────┐ │
│  │  🎬 Director                                 instruction  │ │
│  │  → Emotional Arc, Visual Hook, Narrative Twist            │ │
│  └───────────────────────────────────────────────────────────┘ │
│       ├──────────┬──────────┐                                  │
│  ┌─────────┐┌─────────┐┌─────────┐                            │
│  │ 🟠 감정 ││ 🔵 비주얼││ 🟣 반전 │  generation (병렬)        │
│  │ "실수 속││ "눈물의 ││ "완성된 │                            │
│  │  성장"  ││  양파"  ││  맛"    │                            │
│  │ 1.2K/3.2s│ 1.1K/3.0s│ 1.2K/3.1s│                           │
│  └────┬────┘└────┬────┘└────┬────┘                            │
│       └──────────┼──────────┘                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  🎬 Director                                  evaluation  │ │
│  │  🟠 Emotional Arc  ████████████████████░░░  0.85          │ │
│  │  🔵 Visual Hook    ██████████████░░░░░░░░░  0.72          │ │
│  │  🟣 Narrative Twist████████████░░░░░░░░░░░  0.68          │ │
│  └───────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  🎬 Director  ⚡ decision  Advisor (gap=0.13 < 0.15)      │ │
│  │  추천: 🟠 감정 성장형  |  ✓ 사용자 선택됨 10:01:23        │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ── Phase 2: 전문가 Pipeline ────────────────────────────────── │
│  (handoff → generation → QC → feedback → 재실행 → QC PASS)     │
│                                                                 │
│  ── 세션 통계 ────────────────────────────────────────────────  │
│  Traces: 15 | Tokens: 12.4K | Duration: 1m 23s | QC retries: 1 │
└─────────────────────────────────────────────────────────────────┘
```

### UI 구성 요소

- **트레이스 카드**: 접힌 상태 (agent + type + tokens + latency) / 펼친 상태 (input/output 전문)
- **Decision 카드 (Advisor)**: 3개 옵션 비교표 + 추천 + 사용자 선택 결과
- **정보 밀도 2단계**: 기본 뷰 (role, type, latency) / 디버그 모드 (+ model_id, token_usage, temperature)
- **디버그 토글**: 세션 헤더 우상단, localStorage 지속

---

## 5. 세션 상태 흐름

```
created → phase1_running → phase1_done → phase2_running → completed
    │           │                │              │
    └→ failed   └→ failed        └→ failed      └→ failed
```

| Endpoint | 허용 상태 | 다음 상태 |
|----------|----------|----------|
| `POST /run-debate` | `created` | `phase1_running` → `phase1_done` |
| `POST /select-concept` | `phase1_done` | `phase1_done` (concept 확정만) |
| `POST /run-pipeline` | `phase1_done` (concept 필수) | `phase2_running` → `completed` |
| `POST /send-to-studio` | `completed` | `completed` (변경 없음) |
| `POST /retry` | `failed` | resume/restart 모드 |

V1/V2 공존: `session_type` 컬럼으로 분리 ("free" = V1, "shorts" = V2)

---

## 6. Backend 구현

### DB 스키마 (실제 구현)

**`creative_sessions` 테이블 — V2 추가 컬럼:**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| session_type | String(20) | "free" (V1) / "shorts" (V2) |
| director_mode | String(20) | "auto" / "advisor" |
| concept_candidates | JSONB | Phase 1 완료 시 콘셉트 후보 |
| selected_concept_index | Integer | 선택된 콘셉트 인덱스 |

**`creative_traces` 테이블 — V2 추가 컬럼:**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| phase | String(20) | "concept" / "production" |
| step_name | String(50) | "scriptwriter" / "cinematographer" 등 |
| target_agent | String(50) | handoff/feedback 수신 에이전트 |
| decision_context | JSONB | decision trace 상세 맥락 |
| retry_count | Integer | 피드백 후 재실행 횟수 |

### API 엔드포인트 (6개)

| Method | Endpoint | 설명 | 비동기 |
|--------|----------|------|--------|
| POST | `/sessions/shorts` | 세션 생성 | N |
| POST | `/sessions/{id}/run-debate` | Phase 1 시작 | Y (202) |
| POST | `/sessions/{id}/select-concept` | 콘셉트 확정 | N |
| POST | `/sessions/{id}/run-pipeline` | Phase 2 시작 (SELECT FOR UPDATE) | Y (202) |
| POST | `/sessions/{id}/retry` | 재시도 (resume/restart) | Y (202) |
| POST | `/sessions/{id}/send-to-studio` | Studio로 전송 | N |

비동기 엔드포인트: HTTP 202 반환 → 2초 간격 polling으로 상태 확인

### Backend 파일 구조 (실제)

```
backend/
├── services/
│   ├── creative_shorts.py          # Phase 1 오케스트레이터 (run_debate_v2)
│   ├── creative_debate_agents.py   # 3 Architect + Devil's Advocate + Director 에이전트
│   ├── creative_pipeline.py        # Phase 2 순차 파이프라인 (run_pipeline, 337줄)
│   ├── creative_studio.py          # 세션 생성 + send-to-studio 서비스 (210줄)
│   ├── creative_qc.py              # QC 검증 (validate_scripts/visuals/music/copyright)
│   └── creative_utils.py           # 공통 유틸리티 (parse_json, trace, token, 헬퍼)
├── templates/creative/
│   ├── concept_architect.j2        # Architect 프롬프트
│   ├── devils_advocate.j2          # Devil's Advocate 프롬프트
│   ├── director_evaluate.j2        # Director 평가 프롬프트
│   ├── scriptwriter.j2             # Scriptwriter 프롬프트 (+ multi-char + feedback)
│   ├── cinematographer.j2          # Cinematographer 프롬프트 (+ characters_tags + feedback)
│   ├── sound_designer.j2           # Sound Designer BGM 추천 (+ feedback)
│   ├── copyright_reviewer.j2       # Copyright Reviewer 4관점 검증 (+ feedback)
│   └── qc_visual.j2               # QC 검증 프롬프트
├── routers/creative.py             # V1 + V2 통합 API (401줄)
├── models/creative.py              # CreativeSession, CreativeTrace ORM
├── schemas_creative.py             # Pydantic 스키마 (+ character_ids)
└── tests/test_creative_qc_music.py # validate_music + resolve_characters 테스트 (14개)
```

### 트랜잭션 설계

- **Phase 2 Per-Step Commit**: 각 Step(Scriptwriter/Cinematographer)의 traces + progress + state를 원자적으로 커밋
- **재개 지원**: `pipeline.state`에 완료 Step 결과를 보존 → 실패 지점부터 재개
- **Zombie 감지**: `pipeline.heartbeat` 타임스탬프로 stale 세션 감지 (5분 timeout)

### context JSONB 네임스페이스

```json
{
  "duration": 30, "structure": "Dialogue", "language": "Korean",
  "characters": {
    "A": { "id": 1, "name": "하루", "tags": ["brown_hair", "purple_eyes"] },
    "B": { "id": 2, "name": "미나", "tags": ["blonde_hair", "blue_eyes"] }
  },
  "character_name": "하루",
  "character_tags": ["brown_hair", "purple_eyes"],
  "selected_concept": { "title": "...", "hook": "...", "arc": "..." },
  "pipeline": {
    "current_step": "sound_designer",
    "progress": {
      "scriptwriter": "done", "cinematographer": "done",
      "sound_designer": "running", "copyright_reviewer": "pending"
    },
    "state": { "scriptwriter_result": {...}, "cinematographer_result": {...} },
    "heartbeat": "2026-02-10T10:00:30Z"
  }
}
```

### config.py 상수

```python
CREATIVE_DIRECTOR_SCORE_GAP_THRESHOLD = 0.15
CREATIVE_PIPELINE_MAX_RETRIES = 2
CREATIVE_MIN_CONCEPT_SCORE = 0.6
CREATIVE_PIPELINE_POLL_INTERVAL_MS = 2000
CREATIVE_ZOMBIE_TIMEOUT_SECONDS = 300
```

---

## 7. Frontend 구현

### 자동 전환 뷰 (status 기반)

| 세션 status | 표시 뷰 | 설명 |
|-------------|---------|------|
| `created` | ShortsSetupForm | 주제/설정 입력 |
| `phase1_running` | 스피너 (polling 2초) | Debate 진행 중 |
| `phase1_done` | ConceptCompareView | 3카드 비교 + 선택 |
| `phase2_running` | PipelineProgressView | 스텝 인디케이터 |
| `completed` | SessionResultView | 씬 테이블 + Send |
| `failed` | ErrorView + Retry | 에러 상세 + 재시도 |

디버그 슬라이드오버: 세션 헤더 우상단 🔧 아이콘 → TraceTimeline 패널 (기본 OFF, localStorage)

### Decision 카드 UX (2단계)

- **Summary strip**: 3개 가로 카드 — 제목 + 점수바 + 1줄 요약. 추천 카드에 `border-green-400`
- **Detail drawer**: 카드 클릭 → 아래 확장 (장단점, mood_progression, pacing_note)
- **Select CTA**: 개별 "Select" 버튼 → "Confirm & Start Pipeline" 2단계 확인

### Frontend 파일 구조 (실제)

```
frontend/app/
├── (app)/lab/tabs/
│   └── CreativeLabTab.tsx          # V1/V2 모드 토글 + status 자동 전환
├── components/lab/
│   ├── ShortsSetupForm.tsx         # V2 전용 폼 (presets API 연동, 184줄)
│   ├── CharacterPicker.tsx         # speaker별 캐릭터 드롭다운 (67줄)
│   ├── ShortsActiveView.tsx        # 세션 활성 뷰 (polling + 상태 자동 전환)
│   ├── ConceptCompareView.tsx      # Phase 1 카드 비교 (summary + drawer + CTA)
│   ├── PipelineProgressView.tsx    # Phase 2 스텝 인디케이터 (4 Steps)
│   ├── SessionResultView.tsx       # 씬 테이블 + BGM 추천 + Send to Studio
│   ├── StatusBadge.tsx             # V2 상태 배지 (phase1_running 등)
│   └── TraceTimeline.tsx           # 트레이스 타임라인 (7종 type + 필터)
└── types/creative.ts               # V2 타입 (MusicRecommendation, character_ids 등)
```

---

## 8. 에이전트 프리셋

### Phase 1 (콘셉트 debate)

| Preset | System Prompt 핵심 |
|--------|-------------------|
| `concept:emotional_arc` | 감정 곡선과 캐릭터 성장에 집중. hook은 감정적 긴장에서 만들어라 |
| `concept:visual_hook` | 시각적 임팩트와 첫 3초 훅에 집중. 강렬한 이미지 하나가 전체 영상을 이끈다 |
| `concept:narrative_twist` | 구조적 참신함과 반전에 집중. 예상을 뒤엎는 전개로 사로잡아라 |
| `critic:devils_advocate` | 5관점에서 날카롭게 비판. 대안도 제시 |

### Phase 2 (전문가 협업)

| Preset | System Prompt 핵심 |
|--------|-------------------|
| `expert:scriptwriter` | key_moments → 씬 분할. 2-Pass: Draft → Self-Edit. Multi-Character speaker 규칙 |
| `expert:cinematographer` | Danbooru 태그 비주얼 설계. speaker별 캐릭터 태그. 카메라 다양성 |
| `expert:sound_designer` | concept mood_progression 분석. SAO 프롬프트 생성. 씬 페이싱 고려 |
| `expert:copyright_reviewer` | 4관점 저작권 검증 (스크립트/구조/캐릭터IP/비주얼). PASS/WARN/FAIL |

### Leader

| Preset | System Prompt 핵심 |
|--------|-------------------|
| `leader:creative_director` | hook/arc/feasibility/originality 기준 점수. Pipeline 품질 게이트 |

---

## 9. 성능 예측

### Phase 1 (라운드당)

| Step | LLM Calls | 병렬 | 레이턴시 |
|------|-----------|------|---------|
| 3x Architect | 3 | Yes | 3-4s |
| Devil's Advocate | 1 | No | 2-3s |
| Director 평가 | 1 | No | 2.5-3.5s |
| **라운드 소계** | **5** | | **7.5-10.5s** |

### Phase 2 (순차)

| Step | LLM Calls | 레이턴시 |
|------|-----------|---------|
| Scriptwriter | 1 | 4.5-6s |
| Cinematographer | 1 | 5.5-8s |
| Sound Designer | 1 | 2-3s |
| Copyright Reviewer | 1 | 2-3s |
| **소계** | **4** | **14-20s** |

### 엔드투엔드

| 시나리오 | LLM Calls | 총 시간 |
|----------|-----------|--------|
| 2라운드 + Phase 2 happy | 14 | **29-41s** |
| 3라운드 + Phase 2 happy | 19 | **37-52s** |
| 3라운드 + 1회 retry | 20-22 | **42-60s** |

---

## 10. MVP 범위

### 포함 (구현 완료)

**Phase 1 MVP (2026-02-09)**:
- Phase 1: 3 Architect + Devil's Advocate + Director (Advisor 모드)
- Phase 2: Scriptwriter → QC → Cinematographer → QC (Background Task)
- send-to-studio: Shallow Copy (image_prompt 직접 저장)
- V1/V2 모드 토글 UI + status 기반 자동 전환
- 에이전트 trace 전체 기록 (7종 trace_type)
- 피드백 루프 + 재시도 (max 2회)

**Phase 3 (2026-02-10)**:
- Multi-Character Dialogue: `character_ids` 매핑, speaker별 캐릭터 태그 주입
- Sound Designer: BGM 방향 추천 (SAO 프롬프트), QC 검증 (`validate_music`)
- Copyright Reviewer: 4관점 저작권/독창성 검증, QC 검증 (`validate_copyright`)
- 4개 템플릿 feedback 블록 (retry 시 QC 피드백을 LLM에 주입)
- send-to-studio 서비스 추출 (`creative_studio.py`, StoryboardCharacter 생성)
- ShortsSetupForm SSOT presets API 연동 (구조/언어/duration Backend에서 로드)
- CharacterPicker 컴포넌트 추출 (Dialogue/Narrated Dialogue UI)
- `final_output.music_recommendation` + Frontend BGM 추천 카드

### 제외 (Future)

| 항목 | Phase |
|------|-------|
| Director Auto-pilot 모드 | Phase 4 |
| Reference Analyst (Phase 0 소재 수집) | Phase 4 |
| Deep Parse send-to-studio (12-Layer 태그 분해) | Phase 4 |
| 실시간 파이프라인 WebSocket 알림 | Phase 4 |
| Studio 연동 시 music_recommendation → music_preset_id 자동 매핑 | Phase 4 |

### Frontend 보강 필요 항목

| 항목 | 우선도 | 현재 상태 |
|------|--------|----------|
| StepIndicator (retry 어노테이션) | 중상 | 미구현 (PipelineProgressView로 대체) |
| CheckResultCard (QC PASS/WARN/FAIL) | 높음 | 미구현 |
| DebugSlideOver (우측 패널) | 낮음 | inline 구현 (슬라이드 아님) |
| TraceTimeline Phase 필터 | 중 | Agent 필터만 구현 |
| PipelineProgressView 라이브 티커 | 중상 | 미구현 |
| Music Preset 자동 매핑 (BGM 추천 → music_preset_id) | 중 | 미구현 |

---

## 11. 수락 기준

| # | 기준 | 상태 |
|---|------|------|
| 1 | 세션 생성 후 Phase 1 Debate가 3개 콘셉트를 생성한다 | [x] |
| 2 | Devil's Advocate가 5관점 피드백을 각 콘셉트에 제공한다 | [x] |
| 3 | Director가 점수를 매기고 사용자에게 3카드 비교 뷰를 표시한다 | [x] |
| 4 | 사용자가 콘셉트를 선택하면 Phase 2가 시작된다 | [x] |
| 5 | Scriptwriter가 2-Pass 스크립트를 생성한다 | [x] |
| 6 | Cinematographer가 씬별 Danbooru 태그를 생성한다 | [x] |
| 7 | QC 불합격 시 최대 2회 재실행 후 통과시킨다 | [x] |
| 8 | Send to Studio로 새 스토리보드가 생성된다 | [x] |
| 9 | 모든 에이전트 상호작용이 trace로 기록된다 | [x] |
| 10 | 실패 시 retry로 resume/restart가 가능하다 | [x] |
| 11 | V1/V2 모드 전환이 정상 동작한다 | [x] |
| 12 | Dialogue/Narrated Dialogue에서 speaker별 캐릭터 매핑이 동작한다 | [x] |
| 13 | Sound Designer가 BGM 방향을 추천하고 final_output에 포함된다 | [x] |
| 14 | Copyright Reviewer가 4관점 저작권 검증을 수행한다 | [x] |
| 15 | QC feedback이 retry 시 LLM 프롬프트에 주입된다 | [x] |
| 16 | send-to-studio에서 StoryboardCharacter 레코드가 생성된다 | [x] |

### 성공 지표

| 지표 | MVP 초기 | 장기 목표 | 측정 방법 |
|------|---------|----------|----------|
| 환경-스크립트 Match Rate | 70%+ | 90%+ | QC 자동 검증 |
| Danbooru 태그 적중률 | 90%+ | 95%+ | validate_tags_with_danbooru |
| QC 재실행 비율 | < 30% | < 20% | retry_count > 0인 trace 비율 |
| 전체 파이프라인 시간 | < 60초 | < 45초 | session 생성~완료 시간차 |
