# LLM Provider 추상화 — 멀티 LLM 지원 설계

**상태**: 계획 (미착수)
**최종 업데이트**: 2026-03-15
**관련 문서**: `docs/03_engineering/backend/AGENT_SPEC.md`

---

## 1. 배경 및 목표

### 1-1. 현황 진단

현재 파이프라인은 Gemini SDK에 직결되어 있다.

```
nodes/location_planner.py
  ├─ from google.genai import types          ← SDK 직결
  ├─ types.GenerateContentConfig(            ← Gemini 전용 설정 객체
  │    safety_settings=GEMINI_SAFETY_SETTINGS)
  ├─ gemini_client.aio.models.generate_content()  ← Gemini API 직접 호출
  └─ PROHIBITED_CONTENT 체크                ← Gemini 전용 에러 개념
```

**결합도 현황** (2026-03-15 기준):
- `google.genai` 직접 참조: 노드 7개 + 툴 3개 = 10개 파일
- Gemini 전용 식별자 출현: 53회

### 1-2. 두 번째 문제: trace + fallback 패턴 중복

Gemini 호출 시 trace + PROHIBITED fallback 로직이 4곳에서 각자 구현되어 있다.

| 파일 | 구현 방식 | fallback |
|------|----------|:--------:|
| `_production_utils.py` | `run_production_step` 공통화 | ✅ |
| `gemini_generator.py` | `_call_gemini_with_retry` 독자 구현 | ✅ |
| `tools/base.py` | multi-turn while loop 독자 구현 | ✅ |
| `location_planner.py` | `run_production_step` 미사용, 직접 구현 | ✅ |
| `research.py` | 직접 구현 | ❌ 누락 |
| `_revise_expand.py` | 직접 구현 | ❌ 누락 |

**근본 원인**: `run_production_step`이 인프라(trace + fallback)와 비즈니스 로직(QC + retry + JSON 파싱)을 7개 레이어로 묶어버려, 비즈니스 로직이 다른 케이스는 전체를 직접 구현하게 된다.

```
run_production_step = [trace + fallback] + [QC + retry + JSON 파싱]
                       ↑ 인프라                ↑ 비즈니스 로직
                       (분리되어야 함)
```

### 1-3. 목표

1. **멀티 LLM 지원**: Ollama 등 신규 LLM 추가 시 노드 파일 무수정
2. **인프라 레이어 단일화**: trace + fallback 로직이 한 곳에서만 존재
3. **강제 메커니즘**: convention이 아닌 인터페이스로 준수 강제
4. **점진적 마이그레이션**: 기존 동작을 깨지 않고 단계적으로 교체

---

## 2. 설계

### 2-1. 레이어 구조

```
┌─────────────────────────────────────────┐
│  Business Layer  (nodes/, tools/)       │  QC, JSON 파싱, 상태 관리
│  llm_provider.generate(step, contents)  │  ← LLM을 모름
└─────────────────────┬───────────────────┘
                      │ LLMProvider Protocol
         ┌────────────┴────────────┐
         ▼                        ▼
┌─────────────────┐      ┌─────────────────┐
│ GeminiProvider  │      │ OllamaProvider  │  (향후 추가)
│ google.genai SDK│      │ ollama SDK      │
│ safety_settings │      │ (없음)          │
│ PROHIBITED 처리 │      │ timeout 처리    │
│ llm.record()    │      │ llm.record_text()│
└────────┬────────┘      └────────┬────────┘
         └────────────┬───────────┘
                      ▼
         ┌────────────────────────┐
         │   trace_llm_call()     │  Langfuse GENERATION 기록
         │   (이미 provider-agnostic)│
         └────────────────────────┘
```

### 2-2. 공통 타입 정의

```python
# backend/services/llm/types.py

@dataclass
class LLMConfig:
    """Provider-agnostic 요청 설정."""
    system_instruction: str | None = None
    temperature: float | None = None
    # tools는 provider별 처리 (Function Calling은 GeminiProvider 전용)

@dataclass
class LLMResponse:
    """Provider-agnostic 응답."""
    text: str
    usage: dict[str, int] | None = None  # input/output/total tokens
    raw: Any = None                       # provider raw response (디버깅용)
```

### 2-3. LLMProvider Protocol

```python
# backend/services/llm/provider.py

@runtime_checkable  # isinstance(provider, LLMProvider) 런타임 체크 허용
class LLMProvider(Protocol):
    async def generate(
        self,
        step_name: str,
        contents: str,
        config: LLMConfig,
        model: str | None = None,
    ) -> LLMResponse: ...
```

`@runtime_checkable`을 적용하여 registry 등에서 `isinstance` 검증이 가능하다.
단, Protocol은 structural subtyping이므로 `GeminiProvider(LLMProvider)` 상속 표기는 선택 사항이다.

### 2-4. GeminiProvider 구현

```python
# backend/services/llm/gemini_provider.py

class GeminiProvider:
    """Gemini SDK 래퍼. 429 retry + PROHIBITED fallback + trace 내장."""

    async def generate(
        self,
        step_name: str,
        contents: str,
        config: LLMConfig,
        model: str | None = None,
    ) -> LLMResponse:
        resolved_model = model or GEMINI_TEXT_MODEL
        gemini_config = types.GenerateContentConfig(
            system_instruction=config.system_instruction,
            temperature=config.temperature,
            safety_settings=GEMINI_SAFETY_SETTINGS,  # Gemini 전용
        )

        # 429/5xx retry (gemini_generator._call_gemini_with_retry에서 이전)
        delays = [1, 3]
        response = None
        for attempt in range(3):
            try:
                async with trace_llm_call(name=step_name, model=resolved_model, input_text=contents) as llm:
                    response = await gemini_client.aio.models.generate_content(
                        model=resolved_model,
                        contents=contents,
                        config=gemini_config,
                    )
                    llm.record(response)  # _extract_usage() 내부 호출
                break
            except Exception as exc:
                if attempt < 2 and _is_retryable(exc):
                    await asyncio.sleep(delays[attempt])
                else:
                    raise

        # PROHIBITED_CONTENT fallback (Gemini 전용)
        if not response.text:
            block_reason = _extract_block_reason(response)
            if block_reason and "PROHIBITED" in block_reason:
                logger.warning("[%s][Fallback] PROHIBITED_CONTENT → %s", step_name, GEMINI_FALLBACK_MODEL)
                async with trace_llm_call(name=f"{step_name}_fallback", model=GEMINI_FALLBACK_MODEL, input_text=contents) as llm_fb:
                    response = await gemini_client.aio.models.generate_content(
                        model=GEMINI_FALLBACK_MODEL,
                        contents=contents,
                        config=gemini_config,
                    )
                    llm_fb.record(response)

        return LLMResponse(
            text=response.text or "",
            usage=_extract_usage(response),  # observability._extract_usage() 재사용
            raw=response,
        )
```

`_extract_usage(response)`: `LLMCallResult.record()` 내부 usage 파싱 로직을 `observability.py`에서 module-level 헬퍼로 추출. `GeminiProvider`와 `LLMCallResult` 양쪽에서 재사용.

### 2-5. OllamaProvider 구현 (향후)

```python
# backend/services/llm/ollama_provider.py

class OllamaProvider:
    """Ollama 로컬 LLM 래퍼."""

    def __init__(self, base_url: str, default_model: str):
        self.base_url = base_url
        self.default_model = default_model

    async def generate(
        self,
        step_name: str,
        contents: str,
        config: LLMConfig,
        model: str | None = None,
    ) -> LLMResponse:
        # PROHIBITED_CONTENT 개념 없음 — 안전 필터가 없는 로컬 LLM
        resolved_model = model or self.default_model

        async with trace_llm_call(name=step_name, model=resolved_model, input_text=contents) as llm:
            response = await _call_ollama(
                model=resolved_model,
                prompt=contents,
                system=config.system_instruction,
                temperature=config.temperature,
            )
            llm.record_text(response["response"])  # record() 대신 record_text() 사용

        return LLMResponse(
            text=response["response"],
            usage=None,  # Ollama 토큰 정보는 버전별 상이 — 향후 eval_count 필드로 추가 가능
            raw=response,
        )
```

### 2-6. trace_llm_call 변경 사항

현재 `LLMCallResult.record()`가 Gemini response 객체를 직접 파싱한다.
`record_text()` 메서드를 추가하여 provider-agnostic 기록을 지원한다.

```python
# observability.py 변경

@dataclass
class LLMCallResult:
    generation: Any = None
    output: str = ""
    usage: dict[str, int] | None = None

    def record(self, response: Any) -> None:
        """기존 Gemini response 파싱 (하위 호환 유지)."""
        self.output = _safe_extract_text(response)
        meta = getattr(response, "usage_metadata", None)
        if meta:
            self.usage = { ... }

    def record_text(self, text: str, usage: dict[str, int] | None = None) -> None:
        """Provider-agnostic 기록 (신규). Ollama, OpenAI 등에서 사용."""
        self.output = text
        self.usage = usage
```

또한 `trace_llm_call`의 기본 모델 하드코딩 제거:

```python
# Before
model=model or GEMINI_TEXT_MODEL  # Gemini 전용 기본값

# After
model=model or ""  # provider가 결정, trace에는 실제 사용 모델명 전달
```

### 2-7. DI (의존성 주입) 방식

싱글턴 패턴으로 앱 시작 시 provider를 결정한다.

```python
# config_pipelines.py 추가
LLM_PROVIDER: Literal["gemini", "ollama"] = os.getenv("LLM_PROVIDER", "gemini")
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_DEFAULT_MODEL: str = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.2")

# backend/services/llm/registry.py
_provider: LLMProvider | None = None

def get_llm_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        if LLM_PROVIDER == "ollama":
            _provider = OllamaProvider(OLLAMA_BASE_URL, OLLAMA_DEFAULT_MODEL)
        else:
            _provider = GeminiProvider()
    return _provider
```

---

## 3. 마이그레이션 계획

### Phase A — 인프라 레이어 구축 (신규 파일 + observability 수정)

**신규 생성 (5개)**:

| 파일 | 내용 |
|------|------|
| `backend/services/llm/__init__.py` | 패키지 |
| `backend/services/llm/types.py` | `LLMConfig`, `LLMResponse` |
| `backend/services/llm/provider.py` | `LLMProvider` Protocol |
| `backend/services/llm/gemini_provider.py` | `GeminiProvider` |
| `backend/services/llm/registry.py` | `get_llm_provider()` 싱글턴 |

**수정 (1개)**:

`backend/services/agent/observability.py`
- `record_text(text, usage)` 메서드 추가 — provider-agnostic 기록용
- `trace_llm_call` 기본 모델 `GEMINI_TEXT_MODEL` → `""` 로 변경 (provider가 실제 모델명 전달)
- `_extract_usage(response)` 내부 헬퍼 함수 추출 — `LLMCallResult.record()` 로직에서 분리, `GeminiProvider`에서도 재사용

### Phase B — `_production_utils.py` 교체

`run_production_step` 내부의 `trace_llm_call` + `gemini_client` 직접 호출 블록을 `get_llm_provider().generate()` 호출로 교체.
외부 인터페이스(`run_production_step` 시그니처) 유지 — 이 함수를 사용하는 기존 노드 무수정.

```python
# Before (run_production_step 내부)
async with trace_llm_call(name=step_name, ...) as llm:
    response = await gemini_client.aio.models.generate_content(...)
    llm.record(response)
# PROHIBITED fallback 직접 처리 ...

# After
llm_response = await get_llm_provider().generate(
    step_name=step_name,
    contents=prompt,
    config=LLMConfig(system_instruction=system_instruction),
    model=resolved_model,
)
raw_text = llm_response.text
```

**변경 파일**: `_production_utils.py` 1개

### Phase C — 독립 노드 교체 (중복 제거)

`run_production_step`을 쓰지 않고 직접 구현한 노드들을 `provider.generate()`로 교체.

| 파일 | 변경 내용 | 난이도 |
|------|----------|:------:|
| `location_planner.py` | `trace_llm_call` 직접 호출 → `provider.generate()` | 낮음 |
| `research.py` | 동일 + fallback 누락 해소 | 낮음 |
| `_revise_expand.py` | 동일 + fallback 누락 해소 | 낮음 |
| `review.py` | REVIEW_MODEL 파라미터 전달 방식 변경 | 중간 |
| `writer.py` | planning 단계 교체 | 낮음 |

**변경 파일**: 5개

### Phase D — `gemini_generator.py` 교체

씬 생성 전용 `_call_gemini_with_retry`를 `GeminiProvider.generate()` 기반으로 교체.

**429 retry 처리**: 현재 `_call_gemini_with_retry`는 `delays = [1, 3]` 기반 3회 retry를 직접 구현하고 있다. 이 로직을 `GeminiProvider` 내부로 이동하여 모든 Gemini 호출에 일관 적용한다.

```python
# GeminiProvider 내부 — retry 포함
async def generate(self, ...) -> LLMResponse:
    delays = [1, 3]
    for attempt in range(3):
        try:
            async with trace_llm_call(...) as llm:
                response = await gemini_client.aio.models.generate_content(...)
                llm.record(response)
            break
        except Exception as exc:
            if attempt < 2 and _is_retryable(exc):
                await asyncio.sleep(delays[attempt])
            else:
                raise
    # PROHIBITED fallback ...
```

`gemini_generator.py`의 `generate_script()` 함수는 `get_llm_provider().generate()` 위임으로 단순화.

**변경 파일**: `gemini_generator.py` 1개

### Phase E — `tools/base.py` 교체

Function Calling multi-turn 루프의 각 스텝을 `provider.generate()` 사용.
단, `tools` 파라미터는 Gemini 전용 개념이므로 `LLMProvider` Protocol 외부에 `GeminiProvider` 전용 메서드를 추가한다.
`tools/base.py`는 `GeminiProvider`를 직접 참조하여 `generate_with_tools()`를 호출한다 (OllamaProvider는 FC 미지원 모델 다수이므로 별도 분기).

```python
# GeminiProvider 전용 확장 (Protocol 외부)
async def generate_with_tools(
    self,
    step_name: str,
    contents: list,
    config: LLMConfig,
    tools: list,
    model: str | None = None,
) -> LLMResponse: ...
```

**변경 파일**: `tools/base.py` 1개

### Phase F — OllamaProvider 구현 (실제 Ollama 도입 시점)

Phase A~E 완료 후, `OllamaProvider` 구현 및 `config_pipelines.py` 환경 변수 추가.
노드 파일 변경 없음.

---

## 4. 파일별 변경 범위 요약

```
신규 생성 (5개):
  backend/services/llm/__init__.py
  backend/services/llm/types.py
  backend/services/llm/provider.py
  backend/services/llm/gemini_provider.py
  backend/services/llm/registry.py

수정 (10개):
  backend/services/agent/observability.py     record_text() 추가, _extract_usage() 추출, 기본 모델 제거
  backend/services/agent/nodes/_production_utils.py
  backend/services/agent/nodes/location_planner.py
  backend/services/agent/nodes/research.py
  backend/services/agent/nodes/_revise_expand.py
  backend/services/agent/nodes/review.py
  backend/services/agent/nodes/writer.py
  backend/services/script/gemini_generator.py
  backend/services/creative_agents.py         trace_llm_call 직접 호출 → provider.generate()
  backend/services/agent/tools/base.py        generate_with_tools() 전환 (Phase E)

삭제 없음: 기존 인터페이스 하위 호환 유지
```

---

## 5. 불변 원칙

- **노드 파일은 `google.genai`를 import하지 않는다** — Phase C 완료 후 linting 규칙으로 강제 가능 (`ruff` `banned-import`)
- **`gemini_client` 직접 참조는 `GeminiProvider` 내부에만 허용**
- **`GEMINI_SAFETY_SETTINGS` 직접 참조는 `GeminiProvider` 내부에만 허용**
- **`trace_llm_call`은 Provider 내부에서만 호출** — 비즈니스 노드에서 직접 호출 금지
- **`LLMConfig`에 provider 전용 필드 추가 금지** — provider 전용 설정은 각 Provider 클래스 내부에서 처리

---

## 6. 테스트 계획

### 단위 테스트

| 테스트 | 대상 |
|--------|------|
| `GeminiProvider.generate()` 정상 호출 | mock gemini_client |
| `GeminiProvider.generate()` PROHIBITED fallback 동작 | block_reason 주입 |
| `OllamaProvider.generate()` 정상 호출 | mock ollama client |
| `trace_llm_call.record_text()` | 직접 |
| `get_llm_provider()` 싱글턴 | `LLM_PROVIDER` env 변수별 |

### 통합 테스트

- `run_production_step` 기존 테스트 전부 통과 확인 (Phase B 후)
- 파이프라인 E2E 테스트 (Phase C 후)

---

## 7. 현재 미결 사항

| 항목 | 결정 필요 |
|------|----------|
| Ollama 도입 시점 | Phase F 착수 기준 미정 |
| `tools/base.py` Function Calling | Ollama는 FC 미지원 모델 다수 — 조건 분기 설계 필요 |
| `review.py` REVIEW_MODEL | `LLMConfig`에 `model` 필드 vs `provider.generate(model=...)` 파라미터 — 현재는 후자로 설계, Phase C 착수 시 확정 |
