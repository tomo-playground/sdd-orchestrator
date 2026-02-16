# AI 사고 과정 투명성 UX 패턴 조사

> 작성: UI/UX Engineer Agent | 2026-02-16
> 목적: AI 콘텐츠/대본 작성 도구의 "AI 사고 과정과 중간 결과를 사용자에게 투명하게 보여주는" UX 패턴 조사
> 적용 대상: Shorts Producer -- 스토리보드 AI 생성 파이프라인

---

## 1. 조사 대상 도구별 분석

### 1.1 Runway ML (Gen-3/Gen-4)

**AI 과정 표시 방식:**
- 생성 큐 시스템: "In queue" (0%) -> 퍼센트 진행 -> 완료
- 프레임 호버 프리뷰: 완성 영상의 개별 프레임을 호버로 미리보기
- Gen-4부터 키프레임 가이드/카메라 컨트롤 등 "의도 입력 UI" 제공

**핵심 패턴:**
- **Queue + Progress Bar**: 퍼센트 기반 진행률 표시 (0% ~ 100%)
- **Post-generation Preview**: 생성 후 프레임 단위 호버 프리뷰
- 생성 중간에 사용자 개입 불가 (fire-and-forget)

**우리 프로젝트 적용점:**
- 이미지 생성 시 큐 + 퍼센트 진행률 표시 적용 가능
- SD 이미지 생성 완료 후 후보 이미지 그리드 프리뷰 (현재 일부 구현)

---

### 1.2 Jasper AI

**AI 과정 표시 방식:**
- 2025년 Multi-Agent 플랫폼으로 전환
- **Jasper Canvas**: 캠페인 전체를 한 워크스페이스에서 시각화
- **Jasper Grid**: 시트형 인터페이스로 콘텐츠 파이프라인 구조화
- **Content Pipeline**: 브리프 -> 데이터 -> 브랜드 가이드라인 -> 출시 에셋 자동화

**핵심 패턴:**
- **Campaign-level Cascade**: 상위 메시지 수정 시 하위 모든 채널/에셋에 즉시 반영
- **Pipeline Visualization**: 아이디어 -> 초안 -> 최적화를 노코드 워크플로우로 시각화
- **Agent 역할 분리**: 마케팅 특화 에이전트 여러 개가 역할별로 동작

**우리 프로젝트 적용점:**
- 스토리보드 -> 씬 -> 이미지 -> 렌더링 파이프라인을 Jasper Grid 방식으로 시각화
- 스타일/톤 변경 시 전체 씬에 cascade 반영하는 UX 참조
- Director Agent -> Storyboard Writer -> Image Generator 역할 시각화 참조

---

### 1.3 Notion AI

**AI 과정 표시 방식:**
- **인라인 편집**: 페이지 내에서 직접 AI가 텍스트 수정 (별도 창 없음)
- **AI 블록**: 페이지에 AI 출력 전용 블록 삽입
- **Notion 3.0 Agents (2025.09)**: 최대 20분간 자율 작업하는 에이전트
  - 수백 페이지를 동시에 처리
  - "제안하는 AI" -> "실행하는 AI"로 전환

**핵심 패턴:**
- **Inline Suggestion**: 문서 맥락 안에서 바로 제안 표시 (별도 패널 불필요)
- **Block-level AI Output**: AI 결과를 독립 블록으로 표시, 수락/거절 가능
- **Autonomous Agent with Timeout**: 자율 에이전트에 시간 제한 부여 (20분)

**우리 프로젝트 적용점:**
- 씬 카드 내 인라인 AI 제안 (프롬프트 개선 제안을 씬 카드 안에서 표시)
- AI 생성 결과를 블록 단위로 수락/거절하는 패턴
- AutoRun 모드에서 시간/단계 제한으로 사용자 통제감 유지

---

### 1.4 Sudowrite (Story Engine)

**AI 과정 표시 방식:**
- **Brain Dump -> Outline -> Prose 3단계**: 사용자 아이디어 -> 구조화 -> 산문화
- **Story Bible**: 캐릭터 시트, 세계관 문서를 한 곳에서 관리
- **Canvas**: 캐릭터 설명/컨텍스트/이미지를 드래그&드롭으로 배치
- **Visualize 기능**: 캐릭터/세계관을 이미지로 시각화
- **Credit Usage Indicator**: 생성 전 비용 실시간 추정

**핵심 패턴:**
- **Progressive Disclosure of Story**: 아이디어 -> 아웃라인 -> 세부 -> 산문 순차 공개
- **Story Bible as Context Panel**: AI의 참조 자료를 사용자가 직접 편집
- **Pre-generation Cost Estimate**: 생성 전 크레딧/토큰 예상 표시
- **Guided AI with User Validation**: AI 생성 -> 사용자 검증 -> 다음 단계 반복

**우리 프로젝트 적용점 (가장 높은 유사도):**
- Brain Dump = Topic/Script 입력, Outline = Storyboard, Prose = Scene Text
- Story Bible = Character Builder + Style 설정 (현재 Manage 페이지에 분산)
- 씬별 AI 생성 전 "이 씬에서 이런 이미지를 만들 예정" 미리보기
- 크레딧/토큰 사용 예상 표시 (API 비용 투명성)

---

### 1.5 ChatGPT Canvas

**AI 과정 표시 방식:**
- **2-Pane Layout**: 좌측 Chat + 우측 Editor (영구 문서)
- **Inline Highlight-to-Edit**: 특정 구간 선택 -> 해당 부분만 AI 수정
- **Version History**: "show changes"로 변경 사항 하이라이트
- **Shortcut Actions**: "suggest edits", "adjust length" 등 원클릭 액션
- **Model Reasoning**: GPT-4o가 Canvas를 열 타이밍/편집 범위를 자율 판단

**핵심 패턴:**
- **Side-by-side Chat + Document**: 대화와 결과물을 동시에 볼 수 있는 레이아웃
- **Targeted Edit (Partial Update)**: 전체 재생성 대신 선택 영역만 수정
- **Change Highlighting**: 이전 vs 현재 차이를 시각적으로 표시
- **Quick Action Toolbar**: 자주 쓰는 AI 명령을 버튼화

**우리 프로젝트 적용점:**
- 씬 편집 시 좌측에 AI 대화/제안, 우측에 씬 카드 표시
- 스크립트 부분 수정: 특정 씬 텍스트만 선택해서 AI 개선 요청
- 스토리보드 변경 전후 diff 표시 (씬 추가/삭제/수정 내역)
- Quick Action: "톤 변경", "길이 조절", "더 극적으로" 등 프리셋 버튼

---

### 1.6 Cursor AI

**AI 과정 표시 방식:**
- **Agent Mode**: 에이전트가 계획 -> 실행 -> 검증을 자율 수행
- **Running Commentary**: 에이전트 동작을 실시간 텍스트로 설명
- **Diff Preview**: 변경 사항을 PR 리뷰처럼 green/red diff로 표시
- **Accept/Reject per Change**: 변경 단위로 수락/거절
- **Background Agent**: 별도 브랜치에서 비동기 작업 후 PR 생성
- **Extended Thinking**: 깊은 추론 시 부분 단계를 사용자에게 표시

**핵심 패턴:**
- **Plan -> Execute -> Review 3단계 투명성**
- **Diff-based Change Review**: 변경 사항을 diff 형식으로 제시
- **Granular Accept/Reject**: 전체가 아닌 개별 변경 단위로 승인
- **Async Agent with PR Model**: 비동기 작업 결과를 "리뷰 요청"으로 제시
- **Tool Call Logging**: 어떤 도구를 호출했는지 로그 표시

**우리 프로젝트 적용점:**
- Director Agent의 피드백을 diff 형식으로 표시 (수정 전/후)
- AutoRun 파이프라인에서 각 단계별 도구 호출 로그 표시
- 씬별 Accept/Reject 기능 (AI가 생성한 씬 중 선택적 채택)
- 백그라운드 이미지 생성 -> 완료 시 "리뷰 요청" 알림

---

### 1.7 v0.dev (Vercel)

**AI 과정 표시 방식:**
- **Composite Model Pipeline**: RAG(검색) -> LLM(추론) -> AutoFix(스트리밍 후처리)
- **실시간 미리보기**: 코드 생성과 동시에 UI 렌더링 업데이트
- **Iterative Chat Refinement**: 채팅으로 점진적 수정 요청
- **Step-by-step Planning**: 에이전트가 계획을 세우고 단계별로 실행

**핵심 패턴:**
- **Live Preview during Generation**: 생성 중 실시간 결과 미리보기
- **AutoFix Streaming**: 생성과 동시에 에러 검출/수정 (사용자 모르게)
- **Chat-based Iteration**: "이 부분을 수정해주세요" 대화형 수정
- **Agent Plan Visibility**: "다음에 이걸 할 예정입니다" 사전 공지

**우리 프로젝트 적용점:**
- 스토리보드 생성 시 실시간 씬 카드 추가 애니메이션 (하나씩 나타남)
- AI 프롬프트 자동 검증/수정을 스트리밍으로 표시
- "이 스토리보드에서 5개 씬을 만들 예정입니다" 사전 계획 표시

---

### 1.8 Midjourney

**AI 과정 표시 방식:**
- **2x2 그리드 프리뷰**: 하나의 프롬프트에서 4개 변형 동시 생성
- **Progressive Rendering**: 노이즈 -> 구조 -> 상세 순서로 이미지 점진 공개
- **U(Upscale) / V(Variation) 버튼**: 선택한 이미지를 확대 또는 변형
- **V7 Draft Mode**: 빠른 초안 모드로 먼저 확인 후 고품질 생성
- **Stylization/Weirdness 슬라이더**: 생성 파라미터를 슬라이더로 조절

**핵심 패턴:**
- **Multi-candidate Grid**: 하나의 입력 -> 여러 후보를 동시에 보여주기
- **Progressive Reveal**: 저해상도 -> 고해상도 점진 공개 (기대감 + 중간 확인)
- **Branch from Selection**: 후보 선택 -> 변형/확대 분기
- **Draft -> Final 2단계**: 빠른 초안 -> 정밀 생성 분리

**우리 프로젝트 적용점 (이미지 생성에 직접 적용):**
- SD 이미지 생성 시 후보 그리드 (2x2 또는 1x4) 표시 (현재 candidates로 일부 구현)
- 저해상도 미리보기 -> 선택 -> 고해상도 생성 2단계
- "이 이미지 기반으로 변형" 기능 (img2img 활용)
- 스타일 강도/위어드니스를 슬라이더로 조절하는 UX

---

### 1.9 Suno AI

**AI 과정 표시 방식:**
- 텍스트 프롬프트 -> 30-60초 생성 -> 자동 재생
- 장르/무드 선택 -> AI 작곡 (중간 개입 불가)
- V4.5+부터 "Add Vocals / Add Instrumental" 후처리 도구 제공

**핵심 패턴:**
- **Fire-and-Forget with Auto-play**: 생성 완료 시 자동 재생으로 즉시 확인
- **Post-generation Layering**: 생성 후 레이어(보컬/악기) 추가/제거
- **Simple Input -> Rich Output**: 최소 입력으로 복잡한 결과물 생성

**우리 프로젝트 적용점:**
- 렌더링 완료 시 자동 재생 프리뷰
- TTS/BGM을 씬별로 레이어링하는 후처리 UX 참조
- "Topic 한 줄 입력 -> 전체 스토리보드" 심플 모드 참조

---

### 1.10 Descript

**AI 과정 표시 방식:**
- **텍스트 기반 편집**: 트랜스크립트 편집 = 비디오/오디오 편집 (혁신적 패러다임)
- **Underlord AI (2025.08)**: 자연어 명령으로 편집 워크플로우 실행
  - "polish this for YouTube" 같은 고수준 명령
  - 멀티스텝 편집을 자동 실행하되 사용자가 결과 리뷰
- **Word-level Precision**: 단어 단위 편집, 실시간 타임라인 동기화
- **Filler Word Detection**: 어/음 등 필러 워드 자동 감지 및 하이라이트

**핵심 패턴:**
- **Text-as-Timeline**: 텍스트 편집이 곧 미디어 편집 (직관적 매핑)
- **Natural Language Command**: "유튜브용으로 다듬어줘" 같은 고수준 명령
- **Automated but Reviewable**: AI가 실행하되 사용자가 결과를 리뷰
- **One-click Cleanup**: 필러 워드 일괄 제거 같은 일괄 처리 액션

**우리 프로젝트 적용점:**
- Scene Text 편집 = 렌더링 결과 편집이 되는 직관적 매핑
- "이 스토리보드를 YouTube Shorts에 맞게 다듬어줘" 고수준 명령
- Director Agent 피드백을 "원클릭 적용/무시" 인터페이스로 제공

---

## 2. 패턴별 크로스 분석

### 2.1 Thinking/Reasoning 표시 패턴

| 패턴 | 사용 도구 | 설명 | 적용 우선순위 |
|------|-----------|------|-------------|
| **Collapsible Reasoning Trace** | Cursor, ChatGPT | 접을 수 있는 추론 과정 박스 | **높음** |
| **Running Commentary** | Cursor, v0 | 실시간 텍스트로 현재 동작 설명 | **높음** |
| **Plan Preview** | Cursor, v0 | 실행 전 "이렇게 할 예정" 표시 | 중간 |
| **Confidence Score** | Multi-agent dashboards | 신뢰도를 신호등 색상으로 표시 | 낮음 |
| **Tool Call Log** | Cursor, ChatGPT | 호출한 도구/API 로그 표시 | 중간 |

**ShapeofAI "Stream of Thought" 패턴 정리:**
- 형태: 경계가 있는 박스, 접기/펼치기 가능
- 3가지 표현:
  1. Human-readable Plan (계획)
  2. Execution Log (도구 호출/코드/결과)
  3. Compact Summary (논리적 추론/인사이트/결정)
- 원칙: "행동하기 전에 계획을 보여주라"

---

### 2.2 Multi-Agent 협업 시각화 패턴

| 패턴 | 사용 도구 | 설명 | 적용 우선순위 |
|------|-----------|------|-------------|
| **Agent Card/Tab View** | Jasper, Multi-agent dashboards | 에이전트별 탭 또는 카드 | **높음** |
| **Active Agent Indicator** | Multi-agent dashboards | 현재 활동 중인 에이전트 표시 | **높음** |
| **Threaded Discussion Panel** | Multi-agent dashboards | 에이전트 간 대화를 스레드로 표시 | 중간 |
| **Consensus/Contribution Trace** | Multi-agent dashboards | 각 에이전트 기여도 시각화 | 낮음 |
| **Orchestration Dashboard** | Jasper Grid | 전체 파이프라인 조감도 | 중간 |

---

### 2.3 중간 결과 프리뷰 패턴

| 패턴 | 사용 도구 | 설명 | 적용 우선순위 |
|------|-----------|------|-------------|
| **Multi-candidate Grid** | Midjourney | 여러 후보를 동시에 표시 | **높음** |
| **Progressive Reveal** | Midjourney | 저해상도 -> 고해상도 점진 공개 | 중간 |
| **Live Preview** | v0, Canvas | 생성과 동시에 실시간 미리보기 | **높음** |
| **Draft -> Final** | Midjourney V7, Sudowrite | 빠른 초안 -> 정밀 결과물 | 중간 |
| **Post-generation Layering** | Suno, Descript | 생성 후 레이어 추가/제거 | 낮음 |

---

### 2.4 Human Feedback Loop 패턴

| 패턴 | 사용 도구 | 설명 | 적용 우선순위 |
|------|-----------|------|-------------|
| **Granular Accept/Reject** | Cursor | 개별 변경 단위로 승인/거절 | **높음** |
| **Inline Edit** | Canvas, Notion | 문서 내에서 직접 선택 -> 수정 | **높음** |
| **Checkpoint Approval** | HITL 패턴 | 단계 사이에 사용자 승인 게이트 | **높음** |
| **Parallel Feedback** | 비동기 HITL | AI 계속 진행 + 피드백 비동기 수집 | 낮음 |
| **Quick Action Buttons** | Canvas, Descript | "수락/거절/수정" 원클릭 버튼 | **높음** |

---

### 2.5 Progress/Pipeline 시각화 패턴

| 패턴 | 사용 도구 | 설명 | 적용 우선순위 |
|------|-----------|------|-------------|
| **Percentage Progress Bar** | Runway | 0-100% 진행률 | **높음** |
| **Step Indicator** | v0, Sudowrite | 현재 몇 단계/전체 몇 단계 | **높음** |
| **Pipeline Flowchart** | Jasper Grid | 전체 워크플로우를 흐름도로 표시 | 중간 |
| **Auto-play on Complete** | Suno | 완료 시 자동 재생/표시 | 중간 |
| **Cost/Token Estimate** | Sudowrite, v0 | 생성 전 비용 예상 표시 | 낮음 |

---

## 3. Shorts Producer 적용 제안

### 3.1 AutoRun 파이프라인 투명성 UI (최우선)

현재 AutoRun은 Script -> Storyboard -> Image -> Render를 자동 체인하지만, 사용자에게 중간 과정이 불투명하다.

**제안: Pipeline Progress Panel**

```
┌─────────────────────────────────────────────────┐
│  AutoRun Pipeline                    [Cancel]   │
├─────────────────────────────────────────────────┤
│                                                 │
│  [1. Script]──>[2. Storyboard]──>[3. Image]──>[4. Render]
│     (done)       (active)         (pending)    (pending)
│                                                 │
│  ┌─ Storyboard Agent ──────────────────────┐   │
│  │ "5개 씬으로 구성합니다.                   │   │
│  │  Scene 1: 도입부 - 캐릭터 등장           │   │
│  │  Scene 2: 갈등 - 문제 발생 ..."          │   │
│  │                          [v 접기]         │   │
│  └──────────────────────────────────────────┘   │
│                                                 │
│  Director Feedback:                             │
│  "Scene 3의 전환이 급합니다. 중간 씬 추가 권장" │
│  [Apply] [Dismiss] [Edit]                       │
│                                                 │
└─────────────────────────────────────────────────┘
```

**참조 패턴:** Cursor의 Running Commentary + v0의 Step Indicator + HITL Checkpoint

---

### 3.2 씬별 AI 생성 과정 표시 (높음)

**제안: Scene Card Thinking Trace**

```
┌─ Scene 3 ───────────────────────────────────────┐
│  [이미지 미리보기]     Scene Text:               │
│   ┌──────────┐        "처음 칼을 잡았을 때..."   │
│   │  (2x2    │                                   │
│   │  후보    │        Prompt:                     │
│   │  그리드) │        1girl, kitchen, knife, ...  │
│   └──────────┘                                   │
│                                                  │
│  ▶ AI Reasoning (접기/펼치기)                    │
│  ┌──────────────────────────────────────────┐   │
│  │ Storyboard Writer:                        │   │
│  │  "도입부에서 긴장감을 조성하기 위해        │   │
│  │   close-up + dim_lighting 조합 선택"       │   │
│  │                                           │   │
│  │ Prompt Engineer:                          │   │
│  │  "medium_shot -> cowboy_shot 교체 (Danbooru │   │
│  │   미등록 태그)"                            │   │
│  │  Match Rate: 87%                          │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  [Accept] [Regenerate] [Edit Prompt]             │
└──────────────────────────────────────────────────┘
```

**참조 패턴:** Midjourney 그리드 + Cursor Reasoning Trace + Canvas Quick Actions

---

### 3.3 Director Agent Feedback UI (높음)

현재 Director Agent(Phase 9-4C)의 피드백이 구조화되어 있으나 UI 표시 패턴이 미정의.

**제안: Diff-style Feedback Card**

```
┌─ Director Feedback ──────────────────────────────┐
│                                                   │
│  Overall Score: 7.2/10                           │
│                                                   │
│  Scene 3 수정 권장:                               │
│  ┌────────────────────────────────────────────┐  │
│  │ - "처음 칼을 잡았을 때"                     │  │
│  │ + "칼을 처음 쥔 그 순간"                    │  │
│  │   (사유: 더 간결하고 임팩트 있는 표현)      │  │
│  └────────────────────────────────────────────┘  │
│  [Apply This] [Skip]                             │
│                                                   │
│  Scene 5 추가 권장:                               │
│  ┌────────────────────────────────────────────┐  │
│  │ + 새 씬: "회상 장면으로 감정선 보강"        │  │
│  │   (사유: Scene 4->6 전환이 급격함)          │  │
│  └────────────────────────────────────────────┘  │
│  [Add Scene] [Skip]                              │
│                                                   │
│  [Apply All Suggestions] [Dismiss All]            │
└───────────────────────────────────────────────────┘
```

**참조 패턴:** Cursor Diff + HITL Granular Accept/Reject + Descript One-click Cleanup

---

### 3.4 이미지 생성 Multi-candidate UI (중간)

**제안: Midjourney-style 후보 선택**

```
┌─ Scene 2 Image Generation ─────────────────────────┐
│                                                     │
│  ┌──────────┐  ┌──────────┐                        │
│  │  후보 1   │  │  후보 2   │                        │
│  │  (선택됨) │  │          │                        │
│  │  ★ 87%   │  │  72%     │                        │
│  └──────────┘  └──────────┘                        │
│  ┌──────────┐  ┌──────────┐                        │
│  │  후보 3   │  │  후보 4   │                        │
│  │  81%     │  │  65%     │                        │
│  └──────────┘  └──────────┘                        │
│                                                     │
│  [Use Selected] [Regenerate All] [Vary Selected]   │
│                                                     │
│  ▶ Generation Details                              │
│  Seed: 42 | Steps: 28 | CFG: 7.0 | Time: 12.3s   │
└─────────────────────────────────────────────────────┘
```

**참조 패턴:** Midjourney 2x2 Grid + Match Rate 점수 표시

---

### 3.5 Storyboard 생성 실시간 스트리밍 (중간)

**제안: Streaming Scene Cards**

Gemini가 스토리보드를 생성할 때, 씬이 하나씩 "타이핑되듯" 나타나는 UX.

```
[시간순 흐름]

t=0s:  "5개 씬 생성 중..."
       ┌─ Scene 1 ─┐ (타이핑 중...)
       │ 캐릭터가 │
       │ 등장하며...│
       └───────────┘

t=2s:  ┌─ Scene 1 ─┐ (완료)
       │ (전체 내용)│
       └───────────┘
       ┌─ Scene 2 ─┐ (타이핑 중...)
       │ 갈등이... │
       └───────────┘

t=8s:  모든 씬 완료
       [Review All] [Auto-generate Images]
```

**참조 패턴:** v0 Live Preview + ChatGPT Stream of Thought

---

## 4. 구현 우선순위 매트릭스

| 제안 | 사용자 가치 | 구현 난이도 | 우선순위 |
|------|------------|------------|---------|
| 3.1 Pipeline Progress Panel | 매우 높음 | 중간 | **P0** |
| 3.2 Scene Card Thinking Trace | 높음 | 낮음 | **P0** |
| 3.3 Director Feedback UI | 높음 | 중간 | **P1** |
| 3.4 Multi-candidate Grid | 중간 | 낮음 (기존 candidates 활용) | **P1** |
| 3.5 Streaming Scene Cards | 중간 | 높음 (SSE/WebSocket 필요) | **P2** |

---

## 5. 핵심 설계 원칙 (조사 기반)

조사한 10개 도구에서 공통으로 발견된 원칙:

1. **"행동 전에 계획을 보여주라"** (Plan before Act)
   - 사용자가 AI의 의도를 미리 확인하고 수정할 수 있어야 한다
   - Cursor, v0, Sudowrite 모두 이 패턴을 채택

2. **"보이되 방해하지 말라"** (Visible but Non-intrusive)
   - 추론 과정은 접을 수 있는 박스로 제공 (기본 접힌 상태)
   - 관심 있는 사용자만 펼쳐서 확인
   - ShapeofAI "Stream of Thought" 패턴의 핵심

3. **"세분화된 통제권"** (Granular Control)
   - 전체 수락/거절이 아닌 개별 항목별 선택
   - Cursor의 change-level accept/reject, Midjourney의 U1-U4 선택

4. **"점진적 공개"** (Progressive Disclosure)
   - 한 번에 모든 정보를 보여주지 않고 단계별로 공개
   - Midjourney의 progressive rendering, Sudowrite의 Brain Dump -> Outline -> Prose

5. **"자동이되 리뷰 가능하게"** (Automated but Reviewable)
   - Descript Underlord: AI가 실행하되 사용자가 결과를 리뷰
   - 우리 AutoRun도 동일한 원칙 적용 필요

---

## 6. 출처

### 조사 도구 공식 사이트
- [Runway ML Research - Gen-3 Alpha](https://runwayml.com/research/introducing-gen-3-alpha)
- [Runway Gen-4 Help](https://help.runwayml.com/hc/en-us/articles/37327109429011-Creating-with-Gen-4-Video)
- [Jasper AI - Multi-Agent Platform](https://www.jasper.ai/blog/introducing-first-multi-agent-platform-built-for-marketers)
- [Jasper Canvas](https://www.jasper.ai/canvas)
- [Jasper Grid](https://www.prnewswire.com/news-releases/jasper-introduces-grid-the-interface-powering-ai-native-content-pipelines-302603705.html)
- [Notion AI](https://www.notion.com/product/ai)
- [Notion AI Inline Guide](https://www.eesel.ai/blog/notion-ai-inline)
- [Sudowrite](https://sudowrite.com/)
- [Sudowrite Review 2025](https://skywork.ai/blog/sudowrite-review-2025-story-engine-describe-pricing/)
- [ChatGPT Canvas - OpenAI](https://openai.com/index/introducing-canvas/)
- [ChatGPT Canvas Review 2025](https://skywork.ai/blog/chatgpt-canvas-review-2025-features-coding-pros-cons/)
- [Cursor AI Guide 2025](https://skywork.ai/blog/vibecoding/cursor-2-0-ultimate-guide-2025-ai-code-editing/)
- [v0 by Vercel](https://v0.app/)
- [v0 Composite Model Family](https://vercel.com/blog/v0-composite-model-family)
- [Midjourney Docs](https://docs.midjourney.com/hc/en-us/articles/32631709682573-Discord-Quick-Start)
- [Suno AI](https://www.suno.ai/)
- [Descript](https://www.descript.com/)
- [Descript Underlord Review](https://aitoolanalysis.com/descript-review-2025-text-based-video-editing/)

### UX 패턴 참조
- [ShapeofAI - Stream of Thought Pattern](https://www.shapeof.ai/patterns/stream-of-thought)
- [ShapeofAI - UX Patterns for AI](https://www.shapeof.ai/)
- [Agentic Design Patterns - UI/UX](https://agentic-design.ai/patterns/ui-ux-patterns)
- [Microsoft Design - UX for Agents](https://microsoft.design/articles/ux-design-for-agents/)
- [WEF - UX in Multi-Agent AI](https://www.weforum.org/stories/2025/08/rethinking-the-user-experience-in-the-age-of-multi-agent-ai/)
- [Smashing Magazine - AI Interface Patterns](https://www.smashingmagazine.com/2025/07/design-patterns-ai-interfaces/)
- [UXmatters - AI Agents Creative Teamwork](https://www.uxmatters.com/mt/archives/2025/12/invisible-collaborators-why-ai-agents-are-the-future-of-creative-teamwork.php)
- [RevivalPixel - Multi-Agent UX Case Study](https://www.revivalpixel.com/case-study/designing-a-collaborative-ai-platform-for-multi-agent-reasoning/)
- [HITL Patterns - Zapier](https://zapier.com/blog/human-in-the-loop/)
- [HITL for AI Agents - Permit.io](https://www.permit.io/blog/human-in-the-loop-for-ai-agents-best-practices-frameworks-use-cases-and-demo)
