# Creative Engine API (AI 창작 엔진)

> v3.5: AI 멀티 에이전트 토론 기반 창작 시스템. 여러 AI 에이전트가 토론(debate)을 통해 시나리오 등의 창작물을 생성합니다.
> 라우터 prefix: `/lab/creative`

## Sessions (창작 세션)

### `POST /lab/creative/sessions`
새 창작 세션을 생성합니다.

**Request:**
```json
{
  "task_type": "scenario",
  "objective": "카페에서 벌어지는 로맨스 에피소드",
  "evaluation_criteria": {"originality": {"weight": 0.3, "description": "Novel ideas"}, "coherence": {"weight": 0.4, "description": "Logical flow"}},
  "character_id": 1,
  "context": {"genre": "romance", "mood": "warm"},
  "agent_config": [
    {"preset_id": 1, "role": "writer_bold"},
    {"preset_id": 2, "role": "writer_stable"}
  ],
  "max_rounds": 3
}
```

- `task_type`: `"scenario"` | `"dialogue"` | `"visual_concept"` | `"character_design"` (default: `"scenario"`)
- `evaluation_criteria`: 평가 기준 (`dict[str, {weight, description}]`, optional — 미지정 시 task_type 기본값)
- `agent_config`: 에이전트 프리셋 구성 (optional, 미지정 시 시스템 기본값)
- `max_rounds`: 최대 토론 라운드 수 (default: `3`)

**Response:** `CreativeSessionResponse`

### `GET /lab/creative/sessions`
세션 목록을 조회합니다.

**Query Parameters:**
- `task_type`: string (optional) - 과제 유형 필터
- `limit`: int (optional) - 최대 반환 개수
- `offset`: int (optional) - 페이지 오프셋

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "task_type": "scenario",
      "objective": "카페에서 벌어지는 로맨스 에피소드",
      "status": "running",
      "max_rounds": 3,
      "total_token_usage": null,
      "created_at": "2026-02-07T12:00:00"
    }
  ],
  "total": 1
}
```

### `GET /lab/creative/sessions/{id}`
세션 상세 정보를 조회합니다.

**Response:** `CreativeSessionResponse`

### `POST /lab/creative/sessions/{id}/run-round`
단일 토론 라운드를 실행합니다. 각 에이전트가 순서대로 의견을 제시합니다.

**Request:**
```json
{
  "feedback": "더 극적인 전개를 추가해주세요"
}
```

- `feedback`: string (optional) - 사용자 피드백 (다음 라운드에 반영)

**Response:** `CreativeSessionResponse`

### `POST /lab/creative/sessions/{id}/run-debate`
전체 토론 루프를 실행합니다. `max_rounds`까지 자동으로 라운드를 반복합니다.

**Response:** `CreativeSessionResponse`

### `POST /lab/creative/sessions/{id}/finalize`
토론을 종료하고 선택된 결과물을 확정합니다.

**Request:**
```json
{
  "selected_output": {
    "title": "카페 로맨스",
    "content": "두 사람이 같은 책을 집어드는 순간..."
  },
  "reason": "에이전트 2의 제안이 감성적 흐름이 가장 자연스러움"
}
```

- `selected_output`: dict (required) - 최종 선택된 창작 결과물
- `reason`: string (optional) - 선택 이유

**Response:** `CreativeSessionResponse`

### `POST /lab/creative/sessions/{id}/send-to-studio`
확정된 창작 결과물을 Studio 스토리보드로 내보냅니다. task_type에 따라 변환 방식이 다릅니다:
- `scenario`: content를 `\n\n`로 분리 → 각 scene의 `script` 필드
- `dialogue`: content를 `\n`로 분리 → 각 scene의 `script` 필드
- `visual_concept`: content를 `\n\n`로 분리 → 각 scene의 `description` 필드
- `character_design`: content 전체 → 단일 scene의 `description` 필드

**Request:**
```json
{
  "storyboard_id": null,
  "group_id": 1
}
```

- `storyboard_id`: int (optional) - 기존 스토리보드에 추가, null이면 신규 생성
- `group_id`: int (default: `1`) - 스토리보드가 속할 그룹

**Response:**
```json
{
  "storyboard_id": 42,
  "scenes_created": 5
}
```

### `GET /lab/creative/sessions/{id}/timeline`
세션의 전체 트레이스 타임라인을 조회합니다. 디버깅 및 토론 과정 시각화에 사용됩니다.

**Response:**
```json
{
  "session": { "id": 1, "task_type": "scenario", "..." },
  "rounds": [
    {
      "id": 1,
      "round_number": 1,
      "leader_summary": "Round evaluation summary",
      "round_decision": "continue",
      "best_agent_role": "writer_bold",
      "best_score": 0.85,
      "created_at": "2026-02-07T12:01:00"
    }
  ],
  "traces": [
    {
      "id": 1,
      "round_number": 1,
      "sequence": 0,
      "trace_type": "instruction",
      "agent_role": "leader",
      "input_prompt": "...",
      "output_content": "...",
      "model_id": "gemini-2.0-flash",
      "token_usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
      "latency_ms": 3200,
      "temperature": 0.3,
      "created_at": "2026-02-07T12:01:15"
    }
  ]
}
```

### `DELETE /lab/creative/sessions/{id}`
세션을 소프트 삭제합니다.

**Response:**
```json
{"ok": true}
```

## Task Types (과제 유형)

### `GET /lab/creative/task-types`
사용 가능한 창작 과제 유형 목록을 조회합니다.

**Response:**
```json
{
  "items": [
    {"key": "scenario", "label": "Scenario", "description": "Create original scenarios and scripts for short-form content"},
    {"key": "dialogue", "label": "Dialogue", "description": "Write natural character dialogues with distinct voices"},
    {"key": "visual_concept", "label": "Visual Concept", "description": "Design visual mood boards and cinematic concepts"},
    {"key": "character_design", "label": "Character Design", "description": "Create unique character profiles with visual tag specifications"}
  ]
}
```

## Agent Presets (에이전트 프리셋)

### `GET /lab/creative/agent-presets`
활성 에이전트 프리셋 목록을 조회합니다.

**Response:**
```json
[
  {
    "id": 1,
    "name": "Creative Writer",
    "role_description": "감성적이고 문학적인 시나리오를 작성하는 에이전트",
    "system_prompt": "You are a creative writer specializing in emotional storytelling...",
    "model_provider": "gemini",
    "model_name": "gemini-2.0-flash",
    "temperature": 0.9,
    "is_system": true,
    "created_at": "2026-02-07T12:00:00"
  }
]
```

### `POST /lab/creative/agent-presets`
에이전트 프리셋을 생성합니다.

**Request:**
```json
{
  "name": "Drama Critic",
  "role_description": "극적 구조와 갈등 요소를 분석하는 비평가 에이전트",
  "system_prompt": "You are a drama critic who analyzes narrative structure...",
  "model_provider": "gemini",
  "model_name": "gemini-2.0-flash",
  "temperature": 0.7
}
```

- `model_provider`: string (optional, default: `"gemini"`)
- `model_name`: string (optional, default: config에서 관리)
- `temperature`: float (optional, default: `0.9`)

**Response:** (200 OK) `GET /lab/creative/agent-presets` 단일 항목과 동일

### `PUT /lab/creative/agent-presets/{id}`
에이전트 프리셋을 수정합니다 (비시스템 프리셋만 수정 가능).

**Request:**
```json
{
  "name": "Updated Critic",
  "role_description": "수정된 역할 설명",
  "system_prompt": "Updated system prompt...",
  "model_provider": "gemini",
  "model_name": "gemini-2.0-flash",
  "temperature": 0.8
}
```

**Response:** `GET /lab/creative/agent-presets` 단일 항목과 동일

> **주의**: `is_system: true`인 시스템 프리셋은 수정 불가 (400 Bad Request).

### `DELETE /lab/creative/agent-presets/{id}`
에이전트 프리셋을 삭제합니다 (비시스템 프리셋만 삭제 가능).

**Response:**
```json
{"ok": true}
```

> **주의**: `is_system: true`인 시스템 프리셋은 삭제 불가 (400 Bad Request).
