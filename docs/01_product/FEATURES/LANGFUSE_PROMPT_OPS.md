# LangFuse Prompt Ops — Jinja2 제거 + 네이티브 통합 계획

**상태**: 백로그
**프로젝트 우선순위**: P2 (Infrastructure)
**선행 완료**: LangFuse Prompt Management 전체 이전 (28개 chat 타입, Phase 0~2)
**목적**: Jinja2 의존 제거 → LangFuse 네이티브 통합 → system/user 분리 정합성 확보

---

## 배경

Phase 0~2에서 28개 프롬프트를 LangFuse chat 타입으로 이관했으나, 다음 구조적 문제가 남아있다:

1. **Jinja2 잔존**: LangFuse에 저장된 프롬프트가 Jinja2 문법(`{% if %}`, `{% for %}`, `| tojson`)을 사용. LangFuse가 파일 저장소 역할만 하고 있음
2. **system/user 분리 불가**: 렌더링 후 규칙+데이터가 하나의 문자열로 합쳐져, system_instruction과 contents를 제대로 분리할 수 없음
3. **LangFuse Playground 미활용**: Jinja2 문법 때문에 LangFuse UI에서 직접 테스트 불가
4. **편집 장벽**: 프롬프트 수정 시 Jinja2 문법 지식 필요

2차 개선은 **Jinja2를 완전 제거**하고 LangFuse 네이티브 변수(`{{variable}}` 단순 치환)로 전환하여, 프롬프트 편집·테스트·system/user 분리를 근본적으로 해결한다.

---

## 아키텍처 전환

### AS-IS (Jinja2 의존)

```
LangFuse (저장)        Python (렌더링)           Gemini (호출)
┌─────────────┐       ┌──────────────┐        ┌────────────┐
│ system: 역할 │       │              │        │ system:    │
│ user: Jinja2 │──fetch──→ Jinja2.render() ──→ │  역할(150ch)│
│  {% if %}    │       │  + 데이터 주입  │        │ contents:  │
│  {% for %}   │       │              │        │  전체(14K)  │
│  | tojson    │       └──────────────┘        └────────────┘
└─────────────┘       ← 규칙+데이터 혼합 →      ← 분리 불가 →
```

### TO-BE (LangFuse 네이티브)

```
Python (데이터 준비)     LangFuse SDK (치환)       Gemini (호출)
┌──────────────┐       ┌─────────────┐        ┌────────────┐
│ 조건분기/반복  │       │ system:     │        │ system:    │
│ → 문자열 변환  │──vars──→│  역할+규칙   │──compile──→│  역할+규칙  │
│ json.dumps() │       │  +출력형식   │   ()   │ contents:  │
│              │       │ user:       │        │  데이터만   │
│              │       │  {{변수}} 만 │        │            │
└──────────────┘       └─────────────┘        └────────────┘
                       ← 순수 텍스트 →         ← 완전 분리 →
```

---

## SDK API 검증 결과 (리뷰 반영)

### compile() API 실제 동작

LangFuse Python SDK `ChatPromptClient`에는 `compile(**kwargs)` **단일 메서드만** 존재한다. `compile_system()`/`compile_user()`는 없음.

```python
# 실제 SDK API
prompt = langfuse.get_prompt("pipeline/director", type="chat", label="production")
messages = prompt.compile(**vars)
# 반환: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
```

따라서 **래퍼 함수**로 role별 분리를 구현한다:

```python
@dataclass
class CompiledPrompt:
    system: str          # system 메시지 (역할+규칙)
    user: str            # user 메시지 (데이터)
    langfuse_prompt: Any # trace 연결용 원본 객체

def compile_prompt(template_name: str, **vars) -> CompiledPrompt:
    prompt = langfuse.get_prompt(lf_name, type="chat", label="production")
    messages = prompt.compile(**vars)
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    user = "\n".join(m["content"] for m in messages if m["role"] == "user")
    # 미치환 변수 방어: {{가 남아있으면 경고
    for field in (system, user):
        if "{{" in field:
            logger.warning("[Prompt] 미치환 변수 감지: %s", template_name)
    return CompiledPrompt(system=system, user=user, langfuse_prompt=prompt)
```

### tojson 필터 부재 대응

LangFuse `compile()`은 순수 문자열 치환만 수행. `| tojson` 같은 필터 없음. **Python에서 `json.dumps()` 사전 처리** 필수.

```python
# 8개 템플릿에서 tojson 20회 사용 → 모두 Python 사전 변환
vars = {
    "scenes_json": json.dumps(scenes, ensure_ascii=False, indent=2),
    "concept_json": json.dumps(concept, ensure_ascii=False, indent=2),
}
# LangFuse 프롬프트에서는 {{scenes_json}}으로 단순 치환
```

### Composability 검증 필요

`@@@langfusePrompt:name=shared/rules@@@` 구문이 Python SDK `compile()` 시점에 resolve되는지 미검증. **Sprint 3 착수 전 PoC 필수**. 미지원 시 Python 측에서 여러 prompt를 fetch 후 수동 조합.

---

## 모듈 역할 분리

| 모듈 | 역할 | 관계 |
|------|------|------|
| `prompt_partials.py` (기존) | 재사용 가능한 텍스트 블록 렌더러 | builders가 내부 호출 |
| `prompt_builders.py` (신규) | 템플릿별 vars dict 조립 (조건분기/반복/json.dumps) | partials 호출 + 추가 로직 |
| `langfuse_prompt.py` (수정) | `compile_prompt()` 래퍼 + LangFuse fetch | builders의 결과를 받아 compile |

```
prompt_builders.py                    langfuse_prompt.py
┌─────────────────────┐              ┌─────────────────────┐
│ build_scriptwriter_ │              │ compile_prompt()    │
│   vars(state, ...)  │──vars dict──→│   langfuse.compile()│
│                     │              │   role별 분리        │
│ 내부:               │              │   미치환 변수 방어    │
│  prompt_partials    │              └─────────────────────┘
│  .render_character_ │
│   profile()         │
│  json.dumps(scenes) │
└─────────────────────┘
```

---

## Jinja2 복잡도 분석 (28개 템플릿)

| 등급 | 복잡도 | 개수 | 템플릿 | 전환 난이도 |
|------|-------|------|--------|-----------|
| **S** | 14~21 | 2 | cinematographer, director_plan | 높음 |
| **A** | 10~13 | 7 | create_storyboard 4종, analyze_topic, director_checkpoint, tts_designer | 중 |
| **B** | 6~9 | 9 | scriptwriter, concept_architect, explain, director, review_reflection 등 | 낮음 |
| **C** | 0~5 | 10 | narrative_review, review_evaluate, devils_advocate, edit_scenes 등 | 최소 |

> `director` 프롬프트는 제어문 7개로 B등급 수준 (리뷰 반영: S→B 재분류)

---

## Sprint 계획

### Sprint 0: PoC + 인프라 (선행)

**Sprint 1 착수 전 필수 검증**:

1. **`compile()` 래퍼 PoC**: `CompiledPrompt` 구현 + C등급 1개(narrative_review)로 E2E 테스트
2. **Composability PoC**: `@@@langfusePrompt:...@@@` SDK resolve 여부 확인 → 미지원 시 대안 설계
3. **fallback 호환성**: 로컬 fallback 파일도 `{{variable}}` 형식으로 변환 시 호환 가능한지 확인

### Sprint 1: C등급 10개 전환

**1-1. `compile_prompt()` 래퍼 구현**

```python
# langfuse_prompt.py에 추가
def compile_prompt(template_name: str, **vars) -> CompiledPrompt:
    prompt = langfuse.get_prompt(lf_name, type="chat", label="production")
    messages = prompt.compile(**vars)
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    user = "\n".join(m["content"] for m in messages if m["role"] == "user")
    return CompiledPrompt(system=system, user=user, langfuse_prompt=prompt)
```

**1-2. 호출부 어댑터 (run_production_step)**

```python
async def run_production_step(template_name, data_vars, ...):
    compiled = compile_prompt(template_name, **data_vars)
    # 재시도 시 매번 compile() 호출 (변수 변경 반영)
    for retry in range(max_retries + 1):
        retry_vars = {**data_vars, "feedback": feedback} if retry > 0 else data_vars
        compiled = compile_prompt(template_name, **retry_vars)
        llm_response = await provider.generate(
            contents=compiled.user,
            config=LLMConfig(system_instruction=compiled.system),
            langfuse_prompt=compiled.langfuse_prompt,
        )
```

**1-3. C등급 10개 전환** (복잡도 0~5)

**1-4. gemini_generator.py 마이그레이션** (독자적 system/user 분리 로직 보유)

### Sprint 2: B등급 9개 전환

scriptwriter, concept_architect, explain, **director**, review_reflection, review_unified, scene_expand, sound_designer, writer_planning

**핵심**: `prompt_builders.py` 신규 생성. `prompt_partials.py`의 함수를 내부 호출.

```python
# services/agent/prompt_builders.py

def build_scriptwriter_vars(state, concept, characters, ...) -> dict:
    return {
        "structure_rules": _structure_rules(state["structure"]),
        "character_block": render_character_profile(characters),  # partials 재사용
        "concept_json": json.dumps(concept, ensure_ascii=False, indent=2),
        "script_rules": f"Scene count: {min_scenes}-{max_scenes} scenes",
    }
```

### Sprint 3: A등급 7개 전환

create_storyboard 4종 + analyze_topic + director_checkpoint + tts_designer

**Composability PoC 결과에 따라**:
- 지원 시: `shared/storyboard-rules` 프롬프트로 공통 규칙 분리
- 미지원 시: `prompt_builders.py`에 공유 규칙 Python 상수로 관리

### Sprint 4: S등급 2개 전환 + 정리

cinematographer(21점), director_plan(21점)

**최종 정리**:
- Jinja2 관련 import 제거 (`template_env`, `BaseLoader`, `Environment`)
- `langfuse_prompt.py`에서 `_lf_jinja_env` 제거
- fallback 파일을 `{{variable}}` 형식으로 통일 (Jinja2 문법 제거)
- `prompt_partials.py` → `prompt_builders.py` 통합 검토

---

## Fallback 전략

Jinja2 제거 후에도 로컬 fallback 유지. 단, **fallback 파일도 네이티브 형식으로 통일**:

```
# AS-IS (Jinja2 fallback): Jinja2 문법
{% if structure == "Dialogue" %}Speakers: A, B{% endif %}
{{ scenes | tojson }}

# TO-BE (LangFuse 네이티브 fallback): {{variable}} 단순 치환만
{{structure_rules}}
{{scenes_json}}
```

Jinja2 `Environment`는 `{{variable}}`도 처리 가능하므로, fallback 경로에서도 동일한 vars dict로 렌더링 가능. 변수 형식 불일치 문제 해소.

---

## 전환 중 공존 관리

Sprint 1~4 진행 중 일부 템플릿은 신규 방식, 일부는 기존 Jinja2 방식으로 혼재:

- `compile_prompt()` 래퍼가 LangFuse에서 프롬프트를 가져오면 **네이티브 경로**
- 기존 `get_prompt_template()` → `bundle.template.render()` 는 **Jinja2 경로**
- 두 함수가 공존하며, Sprint별로 호출부를 점진적으로 전환
- **LangFuse 프롬프트 업데이트와 코드 배포는 반드시 동시에** 수행 (Jinja2 `{{`와 LangFuse `{{` 구문 동일하므로)

---

## 구현 우선순위 요약

| Sprint | 대상 | 규모 | 의존성 |
|--------|------|------|--------|
| **0. PoC** | compile 래퍼 + Composability 검증 | ~100줄 | 없음 |
| **1. C등급 + gemini_generator** | 어댑터 + 11개 | ~400줄 + 프롬프트 11개 수정 | Sprint 0 |
| **2. B등급** | 9개 + prompt_builders.py | ~500줄 + 프롬프트 9개 수정 | Sprint 1 |
| **3. A등급** | 7개 (+ Composability or Python 대안) | ~450줄 + 프롬프트 7개 수정 | Sprint 2 |
| **4. S등급 + 정리** | 2개 + Jinja2 제거 + fallback 통일 | ~500줄 + 프롬프트 2개 수정 | Sprint 3 |

> 총 ~1,950줄 (리뷰 반영: 1,350→1,950줄 상향)

---

## 수락 기준 (DoD)

| # | Sprint | 기준 |
|---|--------|------|
| 1 | S0 | compile_prompt() 래퍼가 system/user 분리 반환, 미치환 변수 경고 |
| 2 | S0 | Composability PoC 결과 문서화 (지원/미지원 + 대안) |
| 3 | S1 | C등급 10개 + gemini_generator가 Jinja2 없이 compile()로 동작 |
| 4 | S1 | system_instruction에 규칙, contents에 데이터만 포함 확인 |
| 5 | S1 | LangFuse Playground에서 C등급 프롬프트 직접 테스트 가능 |
| 6 | S2 | B등급 9개 전환. prompt_builders.py 헬퍼 함수 |
| 7 | S3 | A등급 7개 전환. 공통 규칙 재사용 방식 확정 |
| 8 | S4 | S등급 2개 전환. Jinja2 import 전량 제거. fallback 통일 |
| 9 | 전체 | 28개 전체 프롬프트에서 PROHIBITED_CONTENT 발생률 0% |
| 10 | 전체 | 기존 29개 테스트 마이그레이션 + 신규 테스트 통과 |

---

## 테스트 계획

| Sprint | 신규 테스트 | 기존 테스트 마이그레이션 | 범위 |
|--------|-----------|----------------------|------|
| S0 | ~5개 | - | PoC 검증 |
| S1 | ~15개 | ~10개 | compile_prompt(), system/user 분리, gemini_generator |
| S2 | ~10개 | ~10개 | prompt_builders 헬퍼 함수 |
| S3 | ~8개 | ~5개 | A등급, Composability/대안 |
| S4 | ~5개 | ~4개 | S등급, Jinja2 제거 확인, fallback |

---

## 비-목표 (Out of Scope)

- A/B 테스트, Evaluation, Dataset: Jinja2 제거 완료 후 별도 Sprint
- LiteLLM 도입: 별도 항목
- 파이프라인 이상 탐지: 별도 항목
- 데이터 소유권 정리 (LangFuse Score 연동 등): 별도 명세로 분리
