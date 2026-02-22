# Database Schema — Creative Engine (Agents)

> 본 문서는 [DB_SCHEMA.md](DB_SCHEMA.md)에서 분리된 Creative Engine 서브시스템 스키마입니다.

Multi-Agent 협업을 통한 창작 프로세스 관리 시스템.

## `creative_agent_presets`
재사용 가능한 에이전트 페르소나 및 모델 설정.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `name` | String(100) | 에이전트 이름 (Unique) |
| `role_description` | Text | 역할 설명 |
| `system_prompt` | Text | 시스템 프롬프트 |
| `agent_role` | String(50) | 에이전트 역할 (V2: `scriptwriter`, `cinematographer` 등) |
| `category` | String(30) | 카테고리 (`concept`, `production` 등) |
| `model_provider` | String(20) | `gemini`, `ollama` |
| `model_name` | String(50) | 모델명 (e.g. `gemini-1.5-pro`) |
| `temperature` | Float | 생성 다양성 |
| `agent_metadata` | JSONB | 에이전트 추가 설정 (V2 확장용) |
| `is_system` | Boolean | 시스템 프리셋 여부 |
| `deleted_at` | DateTime | Soft Delete 타임스탬프 |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

## `creative_sessions`
에이전트 간의 창작 세션 (Leader Agent가 오케스트레이션).

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `objective` | Text | 세션 목표 |
| `evaluation_criteria` | JSONB | 평가 기준 |
| `character_id` | Integer (FK) | 대상 캐릭터 (Optional) |
| `context` | JSONB | 추가 컨텍스트 |
| `agent_config` | JSONB | 참여 에이전트 구성 |
| `final_output` | JSONB | 최종 결과물 |
| `max_rounds` | Integer | 최대 라운드 수 |
| `total_token_usage` | JSONB | 총 토큰 사용량 |
| `status` | String(20) | 진행 상태 |
| **V2** | | |
| `session_type` | String(20) | 세션 유형 (default: `"shorts"`) |
| `director_mode` | String(20) | 디렉터 모드 (default: `"advisor"`) |
| `concept_candidates` | JSONB | 컨셉 후보 목록 |
| `selected_concept_index` | Integer | 선택된 컨셉 인덱스 |
| `deleted_at` | DateTime | Soft Delete 타임스탬프 |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

## `creative_session_rounds`
세션 내의 각 토의 라운드 요약.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `session_id` | Integer (FK) | 소속 세션 |
| `round_number` | Integer | 라운드 번호 |
| `leader_summary` | Text | 리더의 라운드 요약 |
| `round_decision` | String(20) | 라운드 결정 (`revise`, `approve` 등) |
| `best_agent_role` | String(50) | 최고 점수 에이전트 역할 |
| `best_score` | Float | 최고 점수 |
| `leader_direction` | Text | 다음 라운드 지시사항 |
| `created_at` | DateTime | 생성 시각 (server_default: now()) |

## `creative_traces`
개별 에이전트의 LLM 호출 및 생각(Thought) 추적.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `session_id` | Integer (FK) | 소속 세션 |
| `round_number` | Integer | 라운드 번호 |
| `sequence` | Integer | 순서 |
| `trace_type` | String(20) | `thought`, `action`, `observation` |
| `agent_role` | String(50) | 에이전트 역할 |
| `agent_preset_id` | Integer (FK) | 사용된 프리셋 |
| `input_prompt` | Text | 입력 프롬프트 |
| `output_content` | Text | LLM 응답 |
| `score` | Float | 평가 점수 |
| `feedback` | Text | 피드백 |
| `model_id` | String(100) | 사용된 모델 ID |
| `token_usage` | JSONB | 토큰 사용량 |
| `latency_ms` | Integer | 응답 시간 (ms) |
| `temperature` | Float | 생성 온도 |
| `parent_trace_id` | Integer (FK → creative_traces, SET NULL) | 부모 트레이스 (self-ref) |
| `created_at` | DateTime | 생성 시각 (server_default: now()) |
| **V2** | | |
| `phase` | String(20) | 단계명 |
| `step_name` | String(50) | 스텝명 |
| `target_agent` | String(50) | 대상 에이전트 |
| `decision_context` | JSONB | 결정 컨텍스트 |
| `retry_count` | Integer | 재시도 횟수 (default: 0) |
