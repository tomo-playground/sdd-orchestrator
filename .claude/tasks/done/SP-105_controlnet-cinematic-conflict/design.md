# SP-105 상세 설계: ControlNet Reference AdaIN 시네마틱 태그 충돌 수정

## 변경 파일 요약

| 파일 | 변경 | 난이도 |
|------|------|--------|
| `backend/config.py` | 충돌 태그 frozenset 추가, indoor 가중치 하향 | 낮음 |
| `backend/services/generation_controlnet.py` | 시네마틱 태그 필터 + payload prompt 동기화 | 중간 |
| `backend/services/generation.py` | `apply_controlnet` 후 `payload["prompt"]` 동기화 | 낮음 |
| `backend/services/agent/nodes/_cine_atmosphere.py` | `has_environment_reference` 힌트 수신 | 낮음 |
| `backend/services/agent/nodes/cinematographer.py` | 환경 참조 여부를 atmosphere에 전달 | 낮음 |
| `backend/services/agent/state.py` | `ScriptState`에 `storyboard_id` 필드 추가 (P1-1용) | 낮음 |

> 난이도: **중** (변경 5파일, DB/API 변경 없음)

---

## Must P0-1: Reference AdaIN 활성 시 위험 시네마틱 태그 자동 억제

### 구현 방법

**1. `config.py` — 충돌 태그 정의**

```python
REFERENCE_ADAIN_CONFLICTING_TAGS: frozenset[str] = frozenset({
    "depth_of_field",
    "shallow_depth_of_field",
    "bokeh",
    "blurry_background",
    "lens_flare",
    "chromatic_aberration",
})
```

> `sidelighting` 제외: 조명 방향 태그로 AdaIN 색감 전이와의 직접 충돌 메커니즘 미확인. spec DoD에도 없음.

**2. `generation_controlnet.py` — `_suppress_cinematic_for_adain()` 신규 함수**

- 시그니처: `_suppress_cinematic_for_adain(ctx: GenerationContext) -> list[str]`
- 위치: `_apply_environment_pinning()` 내부, `_apply_reference_adain_from_asset()` 호출 **직전**
- 로직:
  1. 기존 `split_prompt_tokens(ctx.prompt)`로 토큰 분리 (기존 유틸 재사용)
  2. 각 토큰을 `REFERENCE_ADAIN_CONFLICTING_TAGS`와 **정확 매칭** (부분 매칭 방지)
  3. 매칭된 태그 제거, `", ".join(filtered)`로 rejoin (`normalize_prompt_tokens()` 사용 금지 — LoRA 순서 재배치 부작용 방지)
  4. `ctx.prompt` 직접 수정
  5. 반환: 제거된 태그 리스트
- 단일 책임: warning 추가는 호출자(`_apply_environment_pinning()`)가 담당 (기존 `_detect_env_conflict()` 패턴 일관)

**3. `generation.py` — payload prompt 동기화**

```python
# line 252-254
payload = _build_payload(ctx)
_apply_controlnet(payload, ctx, db)
payload["prompt"] = ctx.prompt  # ControlNet 필터가 ctx.prompt를 수정했을 수 있음
```

> **BLOCKER 수정 (R1-Backend Dev)**: `_build_payload()`가 `payload["prompt"] = ctx.prompt`로 먼저 확정한 뒤 `_apply_controlnet()`이 실행되므로, `request.prompt` 수정은 무효. `ctx.prompt`를 수정하고 payload를 재동기화해야 함.

**4. `_apply_environment_pinning()` 시그니처 변경**

```python
def _apply_environment_pinning(
    request: SceneGenerateRequest,
    controlnet_args_list: list,
    warnings: list[str],
    db,
    location_type: str | None = None,
    ctx: GenerationContext | None = None,  # 신규
) -> None:
```

`_apply_environment()`에서 `ctx`를 전달:
```python
_apply_environment_pinning(req, args, ctx.warnings, db, location_type=location_type, ctx=ctx)
```

### 동작 정의

| Before | After |
|--------|-------|
| `ctx.prompt = "girl, kitchen, depth_of_field, bokeh, close-up"` | `ctx.prompt = "girl, kitchen, close-up"` + `payload["prompt"]` 동기화 |
| Reference AdaIN 비활성 시 | 필터 미적용 (기존 동작 유지) |
| `no_humans` 씬 (line 139-142) | `_apply_environment` 자체가 early return → 필터 미적용 |

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| `ctx`가 None (하위 호환) | `_suppress_cinematic_for_adain` 호출 스킵 |
| prompt 토큰에 유사 태그 (`field`, `depth_perception`) | 정확 매칭이므로 오삭제 없음 |
| Reference AdaIN 비활성 (`ENVIRONMENT_REFERENCE_ENABLED=False`) | `_apply_environment()` line 135-136에서 early return → 필터 자체가 호출 안 됨 |

### 영향 범위

- `_apply_environment_pinning()` 내부에서만 동작 — Reference AdaIN 적용 직전
- `ctx.prompt` 수정 후 `generation.py`에서 `payload["prompt"]` 재동기화
- IP-Adapter, Pose ControlNet 등 다른 ControlNet 유형에는 영향 없음

### 테스트 전략 (`backend/tests/test_generation_controlnet.py` 확장)

```python
# RED: 위험 태그가 ctx.prompt에서 제거되는지
def test_suppress_cinematic_tags_removes_conflicting():
    ctx = _make_ctx(prompt="girl, kitchen, depth_of_field, bokeh, close-up")
    removed = _suppress_cinematic_for_adain(ctx)
    assert "depth_of_field" not in ctx.prompt
    assert "bokeh" not in ctx.prompt
    assert "close-up" in ctx.prompt
    assert set(removed) == {"depth_of_field", "bokeh"}

# RED: 부분 매칭 안전성 — 유사 태그가 오삭제되지 않음
def test_suppress_no_partial_match():
    ctx = _make_ctx(prompt="girl, field, depth_perception")
    removed = _suppress_cinematic_for_adain(ctx)
    assert ctx.prompt == "girl, field, depth_perception"
    assert len(removed) == 0

# RED: 충돌 태그 없으면 prompt 변경 없음
def test_suppress_noop_when_no_conflict():
    ctx = _make_ctx(prompt="girl, backlit, light_rays")
    removed = _suppress_cinematic_for_adain(ctx)
    assert ctx.prompt == "girl, backlit, light_rays"
    assert len(removed) == 0

# 통합: _apply_environment() 호출 시 ENABLED=False면 필터 미실행
@patch("services.generation_controlnet.ENVIRONMENT_REFERENCE_ENABLED", False)
def test_apply_environment_skips_when_disabled():
    # _apply_environment() early return → ctx.prompt 변경 없음
    ...
```

### Out of Scope

- `image_prompt` 생성 로직 변경 (compositor)
- `_collect_context_tags()`에 cinematic 키 추가 (2중 주입 위험 — Gemini 자문 결과 드롭)
- LangFuse 프롬프트 변경
- 빈 prompt 방지 가드 (캐릭터/환경 태그가 항상 존재하여 발생 불가)

---

## Must P0-2: 억제된 태그 warning 로그 + debug_payload.warnings 기록

### 구현 방법

`_apply_environment_pinning()` 내부에서 `_suppress_cinematic_for_adain(ctx)`의 반환값(제거된 태그 리스트)을 받아 warning 처리:

```python
removed = _suppress_cinematic_for_adain(ctx) if ctx else []
if removed:
    msg = f"⚠️ AdaIN 충돌 방지: 시네마틱 태그 억제됨 — {', '.join(removed)}"
    logger.warning("[AdaIN Cinematic Filter] Stripped: %s", removed)
    warnings.append(msg)
```

> 단일 책임: `_suppress_cinematic_for_adain()`은 필터링만, warning 추가는 호출자 (`_detect_env_conflict()` 패턴과 일관)

### 동작 정의

| Before | After |
|--------|-------|
| 억제 발생 시 로그 없음 | `logger.warning` + `ctx.warnings` 추가 → `debug_payload.warnings`에 자동 포함 |

### 테스트 전략 (`backend/tests/test_generation_controlnet.py` 확장)

```python
def test_warning_appended_on_suppression():
    ctx = _make_ctx(prompt="girl, bokeh, lens_flare")
    warnings = []
    # _apply_environment_pinning 내부에서 suppress 후 warning 추가 테스트
    removed = _suppress_cinematic_for_adain(ctx)
    if removed:
        warnings.append(f"Stripped: {removed}")
    assert any("bokeh" in w for w in warnings)
```

### Out of Scope

- debug_payload 구조 변경

---

## Should P1-1: Atmosphere Agent에 배경 ControlNet 힌트 전달

### 구현 방법

**1. `_cine_atmosphere.py`**

- `run_atmosphere()` 시그니처 변경:
  ```python
  async def run_atmosphere(
      scenes_json, framing_result, action_result,
      style_section, writer_plan_section,
      has_environment_reference: bool = False,  # 신규
  ) -> dict | None:
  ```
- `_build_prompt()` 시그니처 동일하게 `has_environment_reference` 추가
- `has_environment_reference=True`일 때 `_RULES` 뒤에 조건부 규칙 삽입:
  ```
  ⚠️ 이 영상은 배경 참조 이미지(Reference AdaIN)가 활성화되어 있습니다.
  depth_of_field, bokeh, blurry_background, lens_flare는 배경과 충돌하므로 사용하지 마세요.
  대안: backlit, light_rays, dust_particles 등 비충돌 태그를 활용하세요.
  ```

**2. `cinematographer.py:_run_team_inner()` — 환경 참조 여부 판단**

> **BLOCKER 수정 (R1-Tech Lead)**: `ScriptState`에 `environment_reference_id` 필드 없음. `draft_scenes`에도 미포함 (씬 빌더에서 deferred 처리).

접근 방법: `ScriptState`에 `storyboard_id` 필드 추가 (TypedDict 1필드 + `_request_to_state()` 1줄) → `_run_team_inner()`에서 DB 조회.

```python
# cinematographer.py 내부
def _has_env_reference(storyboard_id: int | None, db) -> bool:
    """스토리보드에 environment_reference_id가 설정된 씬이 있는지 확인."""
    if not storyboard_id:
        return False
    from models.scene import Scene
    return db.query(Scene.id).filter(
        Scene.storyboard_id == storyboard_id,
        Scene.environment_reference_id.isnot(None),
        Scene.deleted_at.is_(None),
    ).first() is not None
```

호출: `run_atmosphere(..., has_environment_reference=_has_env_reference(storyboard_id, db))`

- 첫 실행 (씬 미존재) → `False` 반환 → 기존 동작 유지
- 재실행 (씬 존재, env ref 설정됨) → `True` → LLM에 힌트 전달
- P0 필터가 최종 방어선이므로 첫 실행에서 `False`여도 안전

### 동작 정의

| Before | After |
|--------|-------|
| Atmosphere Agent가 ControlNet 무관하게 모든 cinematic 태그 생성 | `has_environment_reference=True` 시 LLM이 충돌 태그 자제 (soft guardrail) |
| P0 필터만 존재 | 2중 방어: LLM 자제 + 생성 직전 필터 |

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| LLM이 힌트를 무시하고 충돌 태그 생성 | P0 필터가 최종 방어선으로 동작 |
| `has_environment_reference` 미전달 (기본 False) | 기존 동작과 동일, 하위 호환 |
| 첫 실행 (씬 미존재) | DB 조회 결과 `False` → 힌트 미삽입 → P0 필터에 의존 |
| DB 접근 실패 | `_has_env_reference()`에서 `False` 반환 (fail-safe) |

### 영향 범위

- `_cine_atmosphere.py` 시그니처 변경 → `cinematographer.py` 호출부 1곳만 수정
- `cinematographer.py`에 DB 접근 헬퍼 1개 추가 (DB 세션은 이미 사용 가능)

### 테스트 전략 (`backend/tests/test_cinematographer_team.py` 확장)

```python
def test_atmosphere_prompt_includes_adain_hint():
    prompt = _build_prompt(scenes_json, framing, action, style, plan, has_environment_reference=True)
    assert "Reference AdaIN" in prompt or "배경 참조" in prompt

def test_atmosphere_prompt_no_hint_when_no_reference():
    prompt = _build_prompt(scenes_json, framing, action, style, plan, has_environment_reference=False)
    assert "Reference AdaIN" not in prompt
```

### Out of Scope

- LangFuse 프롬프트 변경 (현재 `_RULES`는 코드 내 상수)
- Graph State 스키마 변경

---

## Should P1-2: Indoor Reference AdaIN 가중치 하향

### 구현 방법

`config.py` line 729:
```python
# Before
REFERENCE_ADAIN_WEIGHT_INDOOR = float(os.getenv("REFERENCE_ADAIN_WEIGHT_INDOOR", "0.40"))
# After
REFERENCE_ADAIN_WEIGHT_INDOOR = float(os.getenv("REFERENCE_ADAIN_WEIGHT_INDOOR", "0.30"))
```

### 동작 정의

| Before | After |
|--------|-------|
| Indoor 씬에서 AdaIN weight 0.40 | 0.30으로 하향 → 배경 색감 영향 감소 |

### 영향 범위

- `_apply_reference_adain_from_asset()`에서 자동 적용
- 환경변수 오버라이드 가능 (기존 메커니즘 유지)

### Out of Scope

- Outdoor 가중치 변경 (0.25 유지)
- Default 가중치 변경 (0.35 유지)

---

## Could P2: `_detect_env_conflict()`에 cinematic 충돌 감지 추가

### 구현 방법

`generation_controlnet.py:_detect_env_conflict()`:
- 기존: `LAYER_ENVIRONMENT`만 비교
- 추가: `req.context_tags.get("cinematic", [])` ∩ `REFERENCE_ADAIN_CONFLICTING_TAGS`가 비어있지 않으면 warning 문자열 반환
- P0 필터가 태그를 제거하므로 AdaIN 적용 자체는 중단하지 않음 (정보성 감지)

### Out of Scope

- `_collect_context_tags()`에 cinematic 키 추가 (2중 주입 위험으로 드롭)

---

## 테스트 파일

| 테스트 파일 | 대상 |
|------------|------|
| `backend/tests/test_generation_controlnet.py` | P0 필터 단위 테스트 (`_suppress_cinematic_for_adain`), `_apply_environment_pinning()` 통합 테스트, `payload["prompt"]` 동기화 테스트 |
| `backend/tests/test_cinematographer_team.py` | P1 atmosphere 힌트 전달 + `_build_prompt()` 단위 테스트 |

### 추가 필수 테스트 케이스 (R2 리뷰 반영)

```python
# 통합: _apply_environment_pinning() 경유 시 warning이 ctx.warnings에 전파되는지
def test_pinning_propagates_cinematic_warning():
    ...

# 통합: apply_controlnet() 후 payload["prompt"]가 ctx.prompt와 동기화되는지
def test_payload_prompt_synced_after_controlnet():
    payload = _build_payload(ctx)
    _apply_controlnet(payload, ctx, db)
    payload["prompt"] = ctx.prompt  # generation.py에서 수행
    assert payload["prompt"] == ctx.prompt
```
