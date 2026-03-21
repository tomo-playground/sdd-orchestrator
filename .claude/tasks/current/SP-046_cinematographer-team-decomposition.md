---
id: SP-046
priority: P1
scope: backend
branch: feat/SP-046-cinematographer-team
created: 2026-03-22
status: pending
depends_on:
label: enhancement
assignee: stopper2008
---

## 무엇을
Cinematographer 노드를 팀 구조로 분해 — 350줄 1인 다역 프롬프트를 역할별 서브 에이전트 4명으로 분리

## 왜
- 현재 Cinematographer가 12개 역할(카메라, 액션, 포즈, 환경, 감정, 시네마틱, Ken Burns 등)을 350줄 프롬프트 1회 호출로 처리
- 프롬프트 덩어리가 커서 앞쪽 결정(카메라)과 뒤쪽 결정(액션/포즈)이 모순되는 문제 발생
  - 실제 사례: `close-up + holding_phone + hand_on_cheek` — SDXL attention 경쟁으로 핵심 요소 드롭
- 규칙 기반 충돌 해소(TagRuleCache)는 조합 폭발로 커버 불가
- LLM 후처리(OPT2I 등)는 이미지 생성 후 수습이라 GPU 낭비
- 역할 분배하면 각 에이전트가 좁은 범위에 집중 → 품질 향상 + Compositor가 크로스 도메인 정합성을 에이전틱하게 추론

## 아키텍처

### 현재
```
Writer → Cinematographer(350줄, 12역할, 1회 호출) → Director(사후 검증)
```

### 목표
```
Writer → Director(방향성 지시 — director_plan.visual_direction 추가)
              |
              v
         Cinematographer Team (순차 실행)
              |
              +-- 1) Framing Agent (~80줄)
              |     카메라, 시선, Ken Burns, 서사 구조 매핑
              |     출력: camera, gaze, ken_burns_preset
              |
              +-- 2) Action Agent (~80줄) ← Framing 결과 참조
              |     Stage Direction, 포즈/액션, 소품, 감정
              |     출력: action, pose, emotion, props, controlnet_pose
              |
              +-- 3) Atmosphere Agent (~80줄)
              |     환경/배경, 시네마틱 기법, 장소 연속성
              |     출력: environment, cinematic
              |
              +-- 4) Compositor (~60줄) ← 1+2+3 결과 수신
              |     크로스 도메인 정합성 추론 (규칙 아님)
              |     태그 문법 검증, 최종 JSON 조립
              |     출력: 최종 scenes JSON
              |
         → Director(최종 검증 — 기존과 동일)
```

### 핵심 설계 원칙
- **Compositor는 규칙이 아니라 추론**: "close-up인데 holding_phone → 폰이 프레임에 안 잡힌다" 를 LLM이 판단
- **순차 실행**: Framing → Action(Framing 참조) → Atmosphere → Compositor. 앞 결정이 뒤 에이전트의 컨텍스트
- **Competition과 공존**: 기존 3 Lens 경쟁 구조를 팀 단위로 적용 가능 (Phase 2)
- **Director 변경 최소**: `director_plan`에 `visual_direction` 필드 추가 (톤, 서사 구조, 클라이막스 위치)

## 완료 기준 (DoD)
- [ ] Framing Agent 노드 구현 + LangFuse 프롬프트
- [ ] Action Agent 노드 구현 + LangFuse 프롬프트 (Framing 결과 참조)
- [ ] Atmosphere Agent 노드 구현 + LangFuse 프롬프트
- [ ] Compositor 노드 구현 + LangFuse 프롬프트 (3명 결과 통합 + 정합성 추론)
- [ ] 기존 cinematographer_node를 팀 오케스트레이터로 리팩터링
- [ ] 출력 계약 유지: `cinematographer_result`, `cinematographer_tool_logs`, `visual_qc_result` 키 불변
- [ ] SSE 호환: 4 서브 에이전트 tool_logs → 단일 리스트 병합
- [ ] Director `director_plan`에 `visual_direction` 필드 추가
- [ ] Director `revise_cinematographer` → 팀 재실행 정상 동작
- [ ] 기존 테스트 regression 없음 (cinematographer 관련 테스트 20+개)
- [ ] 프롬프트 충돌 시나리오 테스트 (close-up + holding_phone 등)
- [ ] 린트 통과

## 영향 분석

### Backend 코드
| 파일 | 변경 내용 |
|------|----------|
| `services/agent/nodes/cinematographer.py` | 팀 오케스트레이터로 전환 — `_run()` 내부에서 4 서브 에이전트 순차 호출 |
| `services/agent/nodes/_cine_framing.py` (신규) | Framing Agent 구현 |
| `services/agent/nodes/_cine_action.py` (신규) | Action Agent 구현 |
| `services/agent/nodes/_cine_atmosphere.py` (신규) | Atmosphere Agent 구현 |
| `services/agent/nodes/_cine_compositor.py` (신규) | Compositor 구현 — 정합성 추론 + JSON 조립 |
| `services/agent/state.py` | `DirectorPlan`에 `visual_direction: str` 필드 추가 + 팀 중간 결과 타입 |
| `services/agent/cinematographer_competition.py` | Phase 2에서 팀 단위 경쟁으로 전환 (이 태스크에서는 비활성화 가능) |
| `services/agent/nodes/finalize.py` | `_prompt_conflict_resolver` — Compositor와 역할 중복 검토. 당장은 유지 (방어선) |
| `services/agent/langfuse_prompt.py` | 4개 서브 프롬프트 등록 (LANGFUSE_MANAGED_TEMPLATES + _TEMPLATE_TO_LANGFUSE) |
| `services/agent/prompt_builders_c.py` | 서브 에이전트용 빌더 함수 추가 (build_framing_input 등) |

### LangGraph 그래프 / 라우팅 (출력 계약 유지 필수)
| 파일 | 영향 | 변경 필요 여부 |
|------|------|--------------|
| `services/agent/script_graph.py` | `cinematographer` 노드 등록 + `route_after_cinematographer` | **변경 불필요** — 오케스트레이터가 기존 노드명 유지, 출력 계약 동일 |
| `services/agent/routing.py` | `route_after_cinematographer`, checkpoint → cinematographer 라우트 | **변경 불필요** — 노드명/출력키 불변 |

### 하류 소비자 (cinematographer_result 의존)
| 소비자 | 사용 방식 | 영향 |
|--------|----------|------|
| `nodes/finalize.py` | `cinematographer_result.scenes` → TTS 병합 + 최종 조립 | **변경 불필요** — 출력 구조 `{"scenes": [...]}` 유지 |
| `nodes/tts_designer.py` | `cinematographer_result.scenes` → 씬별 TTS 디자인 | **변경 불필요** |
| `nodes/sound_designer.py` | `cinematographer_result.scenes` → BGM 추천 | **변경 불필요** |
| `nodes/copyright_reviewer.py` | `cinematographer_result` → IP 검토 | **변경 불필요** |
| `nodes/director.py` | `cinematographer_result` → ReAct 검증 + `revise_cinematographer` 재실행 | **변경 불필요** — `_agent_messaging.py`가 cinematographer_node 호출 |
| `nodes/_agent_messaging.py` | `revise_cinematographer` → `cinematographer_node()` 재호출 | **변경 불필요** — 오케스트레이터 진입점 유지 |
| `nodes/explain.py` | `cinematographer_result` → 설명 생성 | **변경 불필요** |
| `routers/_scripts_sse.py` | `cinematographer_result` + `cinematographer_tool_logs` SSE 전송 | **tool_logs 통합 필요** — 4 서브 에이전트 로그를 단일 리스트로 병합 |

### SSE 호환성
- `_NODE_RESULT_KEYS["cinematographer"]` = `["cinematographer_result", "cinematographer_tool_logs"]`
- 오케스트레이터가 4명의 tool_logs를 하나로 합쳐서 `cinematographer_tool_logs`로 반환해야 SSE 클라이언트 변경 불필요

### Frontend (변경 불필요 — 노드명/키 불변 조건)
| 파일 | 의존 방식 | 영향 |
|------|----------|------|
| `hooks/useStreamingPipeline.ts` | `"cinematographer"` 노드명으로 SSE 이벤트 수신 | **변경 불필요** — 노드명 유지 |
| `utils/pipelineSteps.ts` | `cinematographer: "production"` 스텝 매핑 | **변경 불필요** |
| `types/creative.ts` | `PipelineProgress.cinematographer` 타입 | **변경 불필요** |
| `types/index.ts` | `ProductionSnapshot.cinematographer` 타입 | **변경 불필요** |
| `reasoning/ReasoningSections.tsx` | `CinematographerSection` 렌더러 | **변경 불필요** — `cinematographer_result.scenes` 구조 유지 |
| `snapshot/ProductionSnapshotSummary.tsx` | `snapshot.cinematographer` 표시 | **변경 불필요** |
| `chat/messages/PipelineStepCard.tsx` | 파이프라인 단계 카드 | **변경 불필요** |

### Config / 기타
| 파일 | 의존 | 영향 |
|------|------|------|
| `config_pipelines.py` | `CINEMATOGRAPHER_COMPETITION_ENABLED`, `FLASH_THINKING_BUDGET`, 템플릿 매핑 | 서브 에이전트별 thinking budget 분리 검토 (Phase 2) |
| `nodes/_skip_guard.py` | `"cinematographer"` → `"production"` 스테이지 매핑 | **변경 불필요** — 오케스트레이터 레벨에서 skip |
| `creative_qc.py` | `validate_visuals(scenes)` — Compositor 출력 검증 | **변경 불필요** — Compositor가 최종 scenes 전달 |
| `llm_models.py` | `revise_cinematographer` Literal 타입 | **변경 불필요** |
| `scripts/upload_prompts_to_langfuse.py` | `pipeline/cinematographer` 업로드 | **4개 서브 프롬프트 업로드 추가 필요** |

### LangFuse 프롬프트 (가장 큰 작업)
| LangFuse 이름 | 역할 | 원본 규칙 # | 예상 크기 |
|---------------|------|-------------|----------|
| `pipeline/cinematographer` (기존) | 팀 오케스트레이터 시스템 프롬프트로 축소 | - | ~20줄 |
| `pipeline/cinematographer/framing` (신규) | 카메라, 시선, Ken Burns, 서사→비주얼 매핑 | #2, #3, #10, #13 | ~80줄 |
| `pipeline/cinematographer/action` (신규) | 포즈, 액션, 소품, 감정, Stage Direction | #0, #4, #6, #7 | ~80줄 |
| `pipeline/cinematographer/atmosphere` (신규) | 환경, 시네마틱 기법, 장소 연속성 | #5, #8, #12, #14 | ~80줄 |
| `pipeline/cinematographer/compositor` (신규) | 크로스 도메인 정합성 추론 + 태그 검증 + JSON 조립 | #1, #9, #11 | ~60줄 |

현재 `pipeline/cinematographer` 프롬프트(350줄)를 4개로 분해. 기존 프롬프트는 오케스트레이터 역할로 축소하되 label을 `production`에서 내리고 `v2`로 새 프롬프트 세트 운영 가능.

### LangFuse 변수 매핑
| 서브 프롬프트 | 입력 변수 | 출처 |
|--------------|----------|------|
| framing | `scenes_json`, `visual_direction`, `writer_plan_section` | State, Director Plan |
| action | `scenes_json`, `framing_result`, `characters_tags_block`, `stage_directions` | State + Framing 출력 |
| atmosphere | `scenes_json`, `framing_result`, `action_result`, `style_section` | State + Framing/Action 출력 |
| compositor | `framing_result`, `action_result`, `atmosphere_result`, `characters_tags_block` | 3명 출력 전부 |

### Director 변경
| 항목 | 변경 |
|------|------|
| `DirectorPlan` (state.py) | `visual_direction: str` 필드 추가 |
| `pipeline/director/plan` (LangFuse) | `visual_direction` 출력 지시 추가 (톤, 서사 구조, 클라이막스 위치) |
| `director.py` 코드 | 변경 없음 — `director_plan` dict에 새 필드가 자동 포함 |

### Observability (LangFuse Trace)
- 기존: `cinematographer` 1개 trace
- 변경: `cinematographer.framing`, `cinematographer.action`, `cinematographer.atmosphere`, `cinematographer.compositor` 4개 sub-span
- `record_score()` — Compositor 단계에서 `visual_qc_issues` 기록 (기존과 동일 키)

## 제약
- 건드리면 안 되는 것: Director ReAct Loop 로직, Finalize 노드 전체 흐름
- 기존 cinematographer_tools (validate_danbooru_tag, check_tag_compatibility 등) 재활용
- Gemini Flash 4회 호출 추가 비용 허용 (씬 6개 기준 ~$0.01 이하)
- LangFuse 프롬프트 rollback 가능하도록 기존 `pipeline/cinematographer` label 유지 (v1)

## 힌트
- `services/agent/nodes/cinematographer.py` — 현재 350줄 단일 노드
- `services/agent/cinematographer_competition.py` — 3 Lens 병렬 경쟁 (팀 구조 참고)
- `services/agent/tools/cinematographer_tools.py` — 4개 도구 (팀원 공유 가능)
- `services/agent/prompt_builders_c.py` — 기존 빌더 함수 재활용
- `services/agent/langfuse_prompt.py` — `_TEMPLATE_TO_LANGFUSE` dict에 4개 매핑 추가
- LangFuse `pipeline/cinematographer` — 현재 350줄 프롬프트 (분해 대상)
- 근거 논문: PromptSculptor (EMNLP 2025) — 멀티에이전트 프롬프트 최적화
