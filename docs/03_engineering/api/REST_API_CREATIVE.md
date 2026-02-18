# Creative Engine API Specification (v4.0)

> v4.0 (2026-02-18): 소스 기반 최신화. V2 Shorts Pipeline — Multi-Character, Sound Designer, Copyright Reviewer.

Creative Engine은 여러 AI 에이전트가 협업하여 콘텐츠를 창작하는 멀티 에이전트 시스템입니다.
V1(자유형식 debate)과 V2(쇼츠 파이프라인)가 공존하며, `session_type`으로 구분됩니다.

> Agent Presets 라우터 prefix: `/lab/creative` (creative_presets.py)

## 엔드포인트 요약

### V1 — 자유형식 Creative Lab

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/lab/creative/sessions` | 창작 세션 생성 |
| `GET` | `/lab/creative/sessions` | 세션 목록 조회 |
| `GET` | `/lab/creative/sessions/{id}` | 세션 상세 조회 |
| `POST` | `/lab/creative/sessions/{id}/run-round` | 단일 토론 라운드 실행 |
| `POST` | `/lab/creative/sessions/{id}/finalize` | 세션 종료 및 결과 선택 |
| `GET` | `/lab/creative/sessions/{id}/timeline` | Trace 타임라인 조회 |
| `DELETE` | `/lab/creative/sessions/{id}` | 세션 삭제 (soft delete) |

### V2 — Shorts Pipeline

| Method | Endpoint | Description | 비동기 |
|--------|----------|-------------|--------|
| `POST` | `/lab/creative/sessions/shorts` | Shorts 세션 생성 | N (201) |
| `POST` | `/lab/creative/sessions/{id}/run-debate` | Phase 1 Concept Debate 시작 | Y (202) |
| `POST` | `/lab/creative/sessions/{id}/select-concept` | 콘셉트 확정 | N |
| `POST` | `/lab/creative/sessions/{id}/run-pipeline` | Phase 2 Production Pipeline 시작 | Y (202) |
| `POST` | `/lab/creative/sessions/{id}/retry` | 실패 세션 재시도 | Y (202) |
| `POST` | `/lab/creative/sessions/{id}/send-to-studio` | Studio로 전송 (Storyboard 생성) | N |

### Interactive Review (Pause-Review-Resume)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/lab/creative/sessions/{id}/review` | 현재 리뷰 상태 조회 |
| `POST` | `/lab/creative/sessions/{id}/review/message` | QC Agent에 채팅 메시지 전송 |
| `POST` | `/lab/creative/sessions/{id}/review/action` | 승인/수정 요청 (파이프라인 재개) |

### Agent Presets

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/lab/creative/agent-presets` | 에이전트 페르소나 목록 |
| `POST` | `/lab/creative/agent-presets` | 페르소나 생성 |
| `PUT` | `/lab/creative/agent-presets/{id}` | 페르소나 수정 |
| `DELETE` | `/lab/creative/agent-presets/{id}` | 페르소나 삭제 |

---

## V1 Sessions (자유형식)

### `POST /lab/creative/sessions`
새로운 V1 창작 세션을 시작합니다.

**Request:**
```json
{
  "objective": "사이버펑크 배경의 느와르 단편 스토리 기획",
  "evaluation_criteria": {
    "originality": "기존 클리셰 탈피",
    "visual_potential": "화려한 네온 사인과 어두운 골목 대비"
  },
  "character_id": null,
  "context": { "target_audience": "2030 SF 팬", "tone": "Dark & Gritty" },
  "agent_config": [
    { "role": "Director", "model": "gemini-1.5-pro", "preset_id": 1 },
    { "role": "Writer", "model": "gemini-1.5-flash", "preset_id": 2 }
  ],
  "max_rounds": 5
}
```

**Response (201):**
```json
{
  "id": 1,
  "objective": "사이버펑크 배경의 느와르 단편 스토리 기획",
  "status": "created",
  "session_type": "free",
  "rounds": [],
  "created_at": "2026-02-07T10:00:00"
}
```

### `POST /lab/creative/sessions/{id}/run-round`
단일 토론 라운드를 실행합니다.

### `POST /lab/creative/sessions/{id}/finalize`
세션을 종료하고 최종 결과물을 확정합니다.

**Request:**
```json
{
  "selected_output": { "title": "Neon Rain", "plot": "..." },
  "reason": "가장 시각적 묘사가 뛰어남"
}
```

---

## V2 Shorts Pipeline

### `POST /lab/creative/sessions/shorts`
Shorts 전용 세션을 생성합니다. Multi-Character 지원.

**Request:**
```json
{
  "topic": "요리를 처음 배우는 소녀",
  "duration": 30,
  "structure": "Dialogue",
  "language": "Korean",
  "character_ids": { "A": 1, "B": 2 },
  "director_mode": "advisor",
  "max_rounds": 2,
  "references": ["https://example.com/ref1"]
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| topic | string | O | 쇼츠 주제 |
| duration | int | O | 영상 길이 (15/30/45/60) |
| structure | string | O | Monologue / Dialogue / Narrated Dialogue |
| language | string | O | Korean / English / Japanese |
| character_ids | dict[str, int] | X | speaker→character_id 매핑 (예: `{"A": 1, "B": 2, "Narrator": 3}`) |
| director_mode | string | X | "advisor" (기본) / "auto" |
| max_rounds | int | X | Phase 1 최대 라운드 (기본: 2, 최대: 5) |
| references | list[str] | X | 참고 URL/텍스트 |

**Response (201):** `CreativeSessionResponse`

### `POST /lab/creative/sessions/{id}/run-debate`
Phase 1 Concept Debate를 시작합니다 (비동기 BackgroundTask).

**허용 상태**: `created`
**응답**: HTTP 202 + `PipelineStatusResponse`
**상태 전이**: `created` → `phase1_running` → `phase1_done`

```json
{ "status": "phase1_running", "message": "Debate started" }
```

### `POST /lab/creative/sessions/{id}/select-concept`
Phase 1 완료 후 콘셉트를 확정합니다.

**허용 상태**: `phase1_done`

**Request:**
```json
{ "concept_index": 0 }
```

**Response:** `CreativeSessionResponse` (context.selected_concept 설정됨)

### `POST /lab/creative/sessions/{id}/run-pipeline`
Phase 2 Production Pipeline을 시작합니다 (비동기 BackgroundTask).

**허용 상태**: `phase1_done` (selected_concept 필수)
**응답**: HTTP 202 + `PipelineStatusResponse`
**상태 전이**: `phase2_running` → `completed` / `failed`

**Pipeline Steps** (순차):
1. **Scriptwriter** — 2-Pass 스크립트 생성 (Multi-Character speaker 규칙)
2. **Cinematographer** — Danbooru 태그 비주얼 설계 (speaker별 캐릭터 태그)
3. **Sound Designer** — BGM 방향 추천 (SAO 프롬프트)
4. **Copyright Reviewer** — 4관점 저작권/독창성 검증

각 Step은 QC 검증 후 FAIL 시 최대 2회 feedback + retry.

**Progress (context.pipeline.progress):**
```json
{
  "scriptwriter": "done",
  "cinematographer": "done",
  "sound_designer": "running",
  "copyright_reviewer": "pending"
}
```

### `POST /lab/creative/sessions/{id}/retry`
실패한 세션을 재시도합니다.

**허용 상태**: `failed`

**Request:**
```json
{ "mode": "resume" }
```

| mode | 동작 |
|------|------|
| `resume` | 실패 지점부터 재개 (state 보존) |
| `restart` | Phase 2 처음부터 재시작 |

### `POST /lab/creative/sessions/{id}/send-to-studio`
완료된 세션의 결과를 Studio Storyboard로 전송합니다.

**허용 상태**: `completed`

**Request:**
```json
{
  "group_id": 1,
  "title": "요리 소녀 이야기",
  "deep_parse": false
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| group_id | int | O | 대상 그룹 ID |
| title | string | X | 스토리보드 제목 (기본: 세션 objective) |
| deep_parse | bool | X | true: V3 12-Layer 태그 분해 적용 |

**Response:**
```json
{ "storyboard_id": 42, "scene_count": 12 }
```

**동작**:
- Storyboard + Scene 레코드 생성
- `characters` 매핑이 있으면 StoryboardCharacter 레코드 생성
- `deep_parse=true` 시 speaker별 character_id로 `compose_for_character` 호출

### Interactive Review (Pause-Review-Resume)

Pipeline Step 완료 후 QC 점수가 자동 승인 임계값 미달 시, `step_review` 상태로 전환되어 사용자 리뷰를 대기합니다.

#### `GET /lab/creative/sessions/{id}/review`
현재 리뷰 상태와 QC 분석 결과를 조회합니다.

**허용 상태**: `step_review`

**Response:** `StepReviewResponse`
```json
{
  "step": "scriptwriter",
  "result": { "scenes": [...] },
  "qc_analysis": {
    "overall_rating": "needs_revision",
    "score": 0.65,
    "score_breakdown": { "readability": 0.8, "hook": 0.5 },
    "summary": "도입부 훅이 약합니다",
    "issues": [{ "severity": "critical", "category": "hook", "scene": 0, "description": "..." }],
    "strengths": ["대사 자연스러움"],
    "revision_suggestions": ["씬 1 도입부 강화"]
  },
  "messages": [
    { "role": "system", "content": "Script QC complete. Rating: needs_revision", "timestamp": "..." }
  ]
}
```

#### `POST /lab/creative/sessions/{id}/review/message`
QC Agent에 채팅 메시지를 전송합니다. Agent가 QC를 재실행하고 응답합니다.

**허용 상태**: `step_review`

**Request:**
```json
{ "message": "씬 3의 대사가 어색해요" }
```

**Response:** `StepReviewResponse` (messages에 user + agent 메시지 추가)

#### `POST /lab/creative/sessions/{id}/review/action`
승인 또는 수정 요청을 전송합니다. 이후 파이프라인이 자동 재개됩니다.

**허용 상태**: `step_review`

**Request:**
```json
{ "action": "approve" }
```
```json
{ "action": "revise", "feedback": "도입부를 더 강렬하게 수정해주세요" }
```

| action | 동작 |
|--------|------|
| `approve` | 리뷰 데이터 제거 후 다음 step 진행 |
| `revise` | QC 이슈 + 사용자 피드백을 합쳐 해당 step 재실행 |

**Response**: HTTP 202 + `PipelineStatusResponse`

---

### final_output 구조

Pipeline 완료 시 `session.final_output`에 저장되는 데이터:

```json
{
  "scenes": [
    {
      "order": 0,
      "script": "대사 텍스트",
      "speaker": "A",
      "duration": 2.5,
      "camera": "close-up",
      "environment": "kitchen",
      "image_prompt": "1girl, brown_hair, ...",
      "image_prompt_ko": "긴장한 표정의 소녀",
      "context_tags": { "emotion": "nervous", "action": "holding_knife" }
    }
  ],
  "music_recommendation": {
    "prompt": "Gentle acoustic guitar with soft piano, melancholic to hopeful, 90 BPM",
    "mood": "melancholic_to_hopeful",
    "duration": 30,
    "reasoning": "감정 곡선이 우울에서 희망으로 전환되므로..."
  },
  "source": "creative_lab_v2"
}
```

---

## Agent Presets (에이전트 페르소나)

### `GET /lab/creative/agent-presets`
사용 가능한 에이전트 페르소나 목록을 조회합니다.

**Response:**
```json
[
  {
    "id": 1,
    "name": "Creative Director",
    "role_description": "전체적인 연출과 시각적 톤을 결정하는 감독",
    "model_provider": "gemini",
    "model_name": "gemini-2.0-flash",
    "is_system": true
  }
]
```

### `POST /lab/creative/agent-presets`
새 에이전트 페르소나를 생성합니다.

### `PUT /lab/creative/agent-presets/{id}`
기존 페르소나를 수정합니다.

### `DELETE /lab/creative/agent-presets/{id}`
페르소나를 삭제합니다.

---

## 공통 조회 엔드포인트

### `GET /lab/creative/sessions`
세션 목록을 조회합니다. `session_type` 파라미터로 V1/V2 필터링 가능.

**Query Parameters:**
| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| limit | 50 | 최대 반환 수 |
| offset | 0 | 시작 위치 |
| session_type | (전체) | "free" (V1) / "shorts" (V2) |

### `GET /lab/creative/sessions/{id}`
세션 상세를 조회합니다. V2 세션은 `context.pipeline` 네임스페이스에 진행 상태가 포함됩니다.

### `GET /lab/creative/sessions/{id}/timeline`
세션의 전체 Trace 타임라인을 조회합니다.

**Query Parameters:**
| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| phase | (전체) | "concept" / "production" |
| agent_role | (전체) | 에이전트 필터 |
