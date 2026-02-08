# Creative Engine API Specification

> v3.5 (2026-02-07): Multi-Agent Creative Engine introduced.

Creative Engine은 여러 AI 에이전트(Director, Writer, Reviewer 등)가 협업하여 스토리보드, 캐릭터, 세계관 등을 창작하는 멀티 에이전트 시스템입니다.

## 엔드포인트 요약

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/lab/creative/sessions` | 창작 세션 생성 (시작) |
| `GET` | `/lab/creative/sessions` | 세션 목록 조회 |
| `GET` | `/lab/creative/sessions/{id}` | 세션 상세 조회 (Rounds 포함) |
| `POST` | `/lab/creative/sessions/{id}/run-round` | 단일 토론 라운드 실행 |
| `POST` | `/lab/creative/sessions/{id}/run-debate` | 전체 토론 루프 실행 |
| `POST` | `/lab/creative/sessions/{id}/finalize` | 세션 종료 및 결과 선택 |
| `GET` | `/lab/creative/sessions/{id}/timeline` | 전체 사고 과정(Trace) 타임라인 조회 |
| `DELETE` | `/lab/creative/sessions/{id}` | 세션 삭제 |
| `GET` | `/lab/creative/agent-presets` | 에이전트 페르소나 목록 조회 |
| `POST` | `/lab/creative/agent-presets` | 에이전트 페르소나 생성 |
| `PUT` | `/lab/creative/agent-presets/{id}` | 에이전트 페르소나 수정 |
| `DELETE` | `/lab/creative/agent-presets/{id}` | 에이전트 페르소나 삭제 |

---

## Sessions (창작 세션)

### `POST /lab/creative/sessions`
새로운 창작 세션을 시작합니다.

**Request:**
```json
{
  "objective": "사이버펑크 배경의 느와르 단편 스토리 기획",
  "evaluation_criteria": {
    "originality": "기존 클리셰 탈피",
    "visual_potential": "화려한 네온 사인과 어두운 골목 대비"
  },
  "character_id": null,
  "context": {
    "target_audience": "2030 SF 팬",
    "tone": "Dark & Gritty"
  },
  "agent_config": [
    { "role": "Director", "model": "gemini-1.5-pro", "preset_id": 1 },
    { "role": "Writer", "model": "gemini-1.5-flash", "preset_id": 2 }
  ],
  "max_rounds": 5
}
```

**Response:**
```json
{
  "id": 1,
  "objective": "사이버펑크 배경의 느와르 단편 스토리 기획",
  "status": "created",
  "rounds": [],
  "created_at": "2026-02-07T10:00:00"
}
```

### `GET /lab/creative/sessions/{session_id}`
세션의 현재 상태와 라운드 진행 상황을 조회합니다.

**Response:**
```json
{
  "id": 1,
  "status": "running",
  "rounds": [
    {
      "round_number": 1,
      "leader_summary": "초안 작성 완료, 설정 구체화 필요",
      "round_decision": "revise",
      "best_agent_role": "Writer"
    }
  ]
}
```

### `POST /lab/creative/sessions/{session_id}/run-round`
다음 토론 라운드를 실행합니다.

**Response:** Updated Session Object

### `POST /lab/creative/sessions/{session_id}/finalize`
세션을 종료하고 최종 결과물을 확정합니다.

**Request:**
```json
{
  "selected_output": { "title": "Neon Rain", "plot": "..." },
  "reason": "가장 시각적 묘사가 뛰어남"
}
```

**Response:** Updated Session Object (status: `completed`, final_output 채워짐)

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
    "model_name": "gemini-1.5-pro",
    "is_system": true
  }
]
```
