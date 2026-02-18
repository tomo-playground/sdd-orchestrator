# Script Quality & AI Transparency UX

**상태**: 완료 (Phase 9-5A~5E 전체 완료, 2026-02-17)
**출처**: 4-Agent 크로스 분석 합의 (2026-02-17)
**관련**: [AGENTIC_PIPELINE.md](AGENTIC_PIPELINE.md), [AGENT_SPEC.md](../../03_engineering/backend/AGENT_SPEC.md)

---

## 1. 배경 및 문제 정의

### 1-1. 현재 한계

| 문제 | 상세 |
|------|------|
| **서사 품질 미평가** | Review 노드가 구조만 검증 (필드 존재, duration > 0, speaker 유효성). Hook 강도, 감정 곡선, 클라이맥스 임팩트 등 서사 품질은 평가하지 않음 |
| **템플릿 구조 가이드 부재** | `create_storyboard.j2`에 Hook/Rising/Climax/Resolution 분배 지시 없음. Gemini가 자유롭게 생성 → 품질 편차 큼 |
| **AI 과정 불투명** | 사용자에게 최종 결과만 전달. Critic 3컨셉, Director 판단 근거, 각 에이전트 reasoning이 감춰져 있음 |
| **피드백 수단 부족** | Human Gate에서 텍스트 자유 입력만 가능. "뭘 어떻게 수정해야 할지" 모르는 사용자는 피드백 불가 |
| **Concept 선택 불가** | Critic이 3개 컨셉을 생성하지만 자동 선정만 가능. 사용자가 방향 선택에 참여할 수 없음 |

### 1-2. 설계 원칙 (에이전트 합의)

| 원칙 | 설명 |
|------|------|
| **1개를 제대로** | Multi-draft(3개 대본) 대신, 1개 대본의 품질을 극대화 |
| **컨셉은 가볍게** | 3개 전체 대본이 아니라 3개 컨셉(1-2줄)을 비교 |
| **원클릭 피드백** | 사용자가 무엇을 수정할지 모를 때 프리셋 버튼으로 안내 |
| **과정 투명화** | 각 에이전트의 판단 근거를 단계별로 표시 |
| **Progressive Disclosure** | 기본은 간결, 필요 시 상세 확장 |

---

## 2. 서사 품질 평가 (Narrative Review)

### 2-1. 평가 항목 및 가중치

Storyboard Writer 에이전트의 품질 랭킹 기반:

| 항목 | 가중치 | 설명 | 평가 기준 |
|------|--------|------|----------|
| **Hook** | 40% | 첫 씬(3초)의 시선 고정력 | 질문/충격 통계/도발적 진술 패턴 존재 여부 |
| **Emotional Arc** | 25% | 감정 곡선의 상승-하강 존재 | 씬 간 감정 변화, 클라이맥스 존재 |
| **Twist/Payoff** | 20% | 반전 또는 만족스러운 결말 | 마지막 1-2씬의 서사적 보상 |
| **Speaker Tone** | 10% | 화자 톤의 일관성 및 캐릭터성 | 대사 스타일 통일, 캐릭터에 맞는 어조 |
| **Script-Image Sync** | 5% | 대사와 이미지 프롬프트 정합성 | 대사 내용이 이미지로 표현 가능한지 |

### 2-2. 구현 방식

**Hybrid 방식** (Review 노드 확장):

```
현재: 규칙 검증 → (실패 시) Gemini 구조 평가
개선: 규칙 검증 → 서사 품질 평가(Gemini) → 종합 판정
```

- **항상 실행** (규칙 검증 통과 여부와 무관)
- 기존 규칙 검증이 실패하면 서사 평가 스킵 (구조부터 수정)
- 서사 평가 실패 시 fallback: 통과 처리 (기존 동작 유지)

### 2-3. State 확장

```python
class NarrativeScore(TypedDict, total=False):
    hook: float           # 0.0-1.0
    emotional_arc: float
    twist_payoff: float
    speaker_tone: float
    script_image_sync: float
    overall: float        # 가중 평균
    feedback: str         # 개선 제안 (한국어)

class ReviewResult(TypedDict, total=False):
    passed: bool
    errors: list[str]
    warnings: list[str]
    gemini_feedback: str | None
    narrative_score: NarrativeScore | None  # 신규
```

### 2-4. 통과 기준

- `overall >= 0.6`: 통과
- `overall < 0.6`: revise 트리거 (narrative feedback 주입)
- Quick 모드: 서사 평가 **스킵** (비용 절감, 기존 동작 유지)
- Full 모드: 항상 실행

---

## 3. Hook 구조 가이드 (Template Enhancement)

### 3-1. 템플릿 개선

`create_storyboard.j2`에 추가할 구조 지시:

```
## 씬 구조 가이드

각 씬에 서사적 역할(narrative_function)을 부여하세요:

- **hook** (씬 1): 시청자를 3초 안에 사로잡는 장치
  - 패턴: 충격적 질문 / 반직관적 사실 / 강렬한 감정 / 미스터리
  - 예: "죽기 직전, 가장 먼저 떠오른 건..."
- **rising_action** (씬 2-3): 긴장감 상승, 정보 제공
- **climax** (씬 4-5): 감정적 절정, 반전 또는 핵심 메시지
- **resolution** (마지막 씬): 여운 또는 CTA

### 필수: 첫 씬 Hook 강도
첫 씬의 script는 반드시 다음 중 하나를 포함해야 합니다:
1. 질문형: "~했다면?" / "왜 ~일까?"
2. 충격형: 반직관적 사실이나 통계
3. 감정형: 극단적 감정 상태 묘사
4. 미스터리형: 불완전한 정보 → 궁금증 유발
```

### 3-2. Gemini 출력 확장

```json
{
  "scenes": [
    {
      "scene_number": 1,
      "narrative_function": "hook",
      "script": "...",
      "image_prompt": "..."
    }
  ]
}
```

- 기존 `narrative_function` 필드는 reasoning으로 이미 존재
- 템플릿에서 **필수 출력**으로 격상

---

## 4. Concept Gate

### 4-1. 개요

Critic이 생성한 3개 컨셉을 사용자에게 노출하여 방향 선택 참여를 가능하게 한다.

```
현재: Critic → (자동 선정) → Writer
개선: Critic → [Concept Gate interrupt] → 사용자 선택 → Writer
```

### 4-2. 적용 범위

| Preset | Concept Gate |
|--------|-------------|
| Quick | 없음 (Critic 자체 없음) |
| Full Auto | **자동 선정** (현재와 동일, interrupt 없음) |
| Creator | **사용자 선택** (interrupt) |

### 4-3. 컨셉 표시 형태

```json
{
  "type": "concept_selection",
  "concepts": [
    {
      "id": 1,
      "label": "Emotional Arc",
      "summary": "첫사랑의 설렘에서 이별까지, 감정의 롤러코스터",
      "hook_preview": "처음 눈이 마주쳤을 때...",
      "tone": "서정적, 감성적",
      "score": 0.85
    },
    {
      "id": 2,
      "label": "Visual Hook",
      "summary": "강렬한 비주얼로 시작, 반전 엔딩",
      "hook_preview": "피로 물든 하늘 아래...",
      "tone": "긴박한, 미스터리",
      "score": 0.78
    },
    {
      "id": 3,
      "label": "Narrative Twist",
      "summary": "평범한 일상에서 시작, 반전 폭탄",
      "hook_preview": "그날도 평범한 하루였다...",
      "tone": "일상적 → 충격적",
      "score": 0.72
    }
  ]
}
```

### 4-4. State 확장

```python
class ScriptState(TypedDict, total=False):
    # ... 기존 필드 ...
    selected_concept_id: int | None     # 사용자 선택 컨셉 (1/2/3)
    concept_gate_shown: bool            # Concept Gate 노출 여부
```

### 4-5. 라우팅 변경

```
현재: critic → writer
개선: critic → concept_gate → writer
       └─ (Full Auto) → 자동 선정 → writer (interrupt 없음)
```

- `route_after_critic()` 신규
- Creator 모드: `interrupt()` → 사용자 컨셉 선택
- Full Auto 모드: 기존 자동 선정 로직 유지

---

## 5. 프리셋 피드백 버튼 (One-Click Feedback)

### 5-1. Human Gate 피드백 프리셋

| 버튼 라벨 | revision_feedback 주입 | 대상 |
|-----------|----------------------|------|
| **후킹 강화** | "첫 씬의 Hook을 더 강렬하게 수정. 질문형/충격형/감정형 중 하나로 변경" | Writer (revise) |
| **더 극적으로** | "전체 감정 곡선의 진폭을 키우고 클라이맥스를 더 강렬하게" | Writer (revise) |
| **톤 변경** | "화자의 톤을 {선택}으로 변경" + 톤 서브 선택지 | Writer (revise) |
| **짧게 줄이기** | "불필요한 씬을 제거하고 핵심만 남기기" | Writer (revise) |
| **직접 수정** | 텍스트 입력 모드 전환 | Writer (revise) |

### 5-2. Concept Gate 피드백

| 버튼 | 동작 |
|------|------|
| **컨셉 1/2/3 선택** | 해당 컨셉 ID로 Writer 실행 |
| **다시 생성** | Critic 재실행 (revision_count 증가) |
| **직접 입력** | 사용자가 컨셉 텍스트 직접 작성 |

---

## 6. AI Transparency UX

### 6-1. Pipeline Stepper

현재 SSE 진행률을 시각적 스테퍼로 변환:

```
[Research] → [Concept] → [Script] → [Review] → [Production] → [Director] → [Done]
    ✓           ✓          ●(진행중)
```

- 각 스텝 클릭 시 해당 에이전트의 reasoning 표시
- 병렬 노드(tts/sound/copyright)는 하나의 [Production] 스텝으로 묶기

### 6-2. Agent Reasoning Display

각 에이전트의 판단 근거를 확장 가능한 패널로 표시:

```
▶ Critic (컨셉 토론)
  ├─ Emotional Arc: "첫사랑 테마 → 보편적 공감" (0.85)
  ├─ Visual Hook: "강렬한 비주얼 → 초반 이탈 방지" (0.78)
  └─ Winner: Emotional Arc (평가자: 감정 곡선 최적)

▶ Review (구조 검증)
  ├─ 규칙: 5/5 통과
  └─ 서사: Hook 0.8 | 감정 0.7 | 반전 0.9 → Overall 0.80

▶ Director (통합 검증)
  └─ Decision: approve (비주얼-음성 일관성 확인)
```

### 6-3. Narrative Score Visualization

```
Hook         ████████░░  0.8
Emotion      ███████░░░  0.7
Twist        █████████░  0.9
Tone         ██████░░░░  0.6
Sync         ████████░░  0.8
─────────────────────────
Overall      ████████░░  0.80
```

### 6-4. Scene-Level Editing (향후)

| 기능 | 설명 |
|------|------|
| **Accept** | 개별 씬 승인 (수정 불필요) |
| **Edit** | 인라인 텍스트 편집 |
| **Regenerate** | 해당 씬만 재생성 (나머지 유지) |
| **Feedback** | 씬 단위 피드백 ("이 씬만 더 극적으로") |

---

## 7. 구현 Phase

### Phase 9-5A: Narrative Quality Foundation (Backend)

| # | 작업 | 분류 |
|---|------|------|
| 1 | `create_storyboard.j2` Hook 구조 가이드 추가 | Template |
| 2 | `NarrativeScore` TypedDict + `ReviewResult` 확장 | State |
| 3 | Review 노드에 서사 품질 평가 추가 (Gemini 1회) | Node |
| 4 | Revise 노드에 narrative feedback 주입 | Node |
| 5 | 서사 평가 Jinja2 템플릿 작성 (`creative/narrative_review.j2`) | Template |
| 6 | 테스트 (서사 평가 로직 + 라우팅 분기) | Test |

### Phase 9-5B: Concept Gate (Backend + Frontend)

| # | 작업 | 분류 |
|---|------|------|
| 1 | `concept_gate` 노드 구현 (Creator: interrupt, Full Auto: pass-through) | Node |
| 2 | Critic 출력에 concept summary/hook_preview 추가 | Template |
| 3 | `route_after_critic()` 라우팅 함수 추가 | Routing |
| 4 | ScriptState에 `selected_concept_id`, `concept_gate_shown` 추가 | State |
| 5 | `/scripts/resume` API에 concept_selection 타입 추가 | API |
| 6 | Frontend: Concept 선택 카드 UI | Frontend |
| 7 | Frontend: "다시 생성" / "직접 입력" 액션 | Frontend |
| 8 | 테스트 (concept gate interrupt/resume, 라우팅) | Test |

### Phase 9-5C: AI Transparency UX (Frontend)

| # | 작업 | 분류 |
|---|------|------|
| 1 | Pipeline Stepper 컴포넌트 (SSE 노드 매핑) | Frontend |
| 2 | Agent Reasoning 확장 패널 | Frontend |
| 3 | Narrative Score 시각화 (바 차트) | Frontend |
| 4 | Explain Node 결과 표시 개선 | Frontend |

### Phase 9-5D: Interactive Feedback (Backend + Frontend)

| # | 작업 | 분류 |
|---|------|------|
| 1 | Human Gate 프리셋 피드백 버튼 5종 | Frontend |
| 2 | 프리셋 → structured revision_feedback 변환 로직 | Backend |
| 3 | Concept Gate 피드백 버튼 (선택/재생성/직접입력) | Frontend |
| 4 | 테스트 (프리셋 피드백 주입 → revise 동작 확인) | Test |

---

## 8. 외부 UX 리서치 기반

**참조**: [AI_TRANSPARENCY_UX_RESEARCH.md](../../02_design/AI_TRANSPARENCY_UX_RESEARCH.md)

10개 AI 도구 분석에서 도출된 5대 원칙:

1. **Plan before Act**: 실행 전 계획 표시 (Concept Gate)
2. **Visible but Non-intrusive**: 진행 상황 표시하되 방해하지 않음 (Pipeline Stepper)
3. **Granular Control**: 세밀한 제어 제공 (Scene-level editing)
4. **Progressive Disclosure**: 기본 간결, 상세 확장 (Reasoning panel)
5. **Automated but Reviewable**: 자동이지만 검토 가능 (Narrative Score)

---

## 9. 영향 범위

### Backend

| 파일 | 변경 |
|------|------|
| `services/agent/state.py` | `NarrativeScore` 추가, `ReviewResult` 확장, `selected_concept_id` 추가 |
| `services/agent/nodes/review.py` | 서사 품질 평가 로직 추가 |
| `services/agent/nodes/revise.py` | narrative feedback 주입 |
| `services/agent/nodes/concept_gate.py` (신규) | Concept Gate interrupt |
| `services/agent/nodes/critic.py` | concept summary 출력 추가 |
| `services/agent/routing.py` | `route_after_critic()` 추가 |
| `services/agent/script_graph.py` | concept_gate 노드 + 엣지 추가 |
| `templates/creative/narrative_review.j2` (신규) | 서사 평가 프롬프트 |
| `templates/creative/create_storyboard.j2` | Hook 구조 가이드 추가 |
| `routers/scripts.py` | concept_selection resume 타입, SSE 매핑 업데이트 |
| `schemas.py` | `ScriptResumeRequest` concept_selection 필드 |

### Frontend

| 파일 | 변경 |
|------|------|
| Script 탭 | Pipeline Stepper, Concept Gate UI, Preset Feedback 버튼 |
| Reasoning 패널 | Agent별 판단 근거 확장 표시 |
| Narrative Score | 바 차트 시각화 컴포넌트 |
| SSE 핸들러 | concept_selection interrupt 타입 처리 |

### 그래프 구조 변경 (Full 모드)

```
현재 (14노드):
START → research → critic → writer → review → ...

개선 (15노드):
START → research → critic → concept_gate → writer → review → ...
                    └─ (Full Auto) → 자동 통과 → writer
```
