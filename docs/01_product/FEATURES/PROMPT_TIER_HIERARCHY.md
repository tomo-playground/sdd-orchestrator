# Prompt 3-Tier 소유권 계층 구조

**상태**: ✅ 구현 완료 (2026-03-02)

## 문제

12-Layer 프롬프트 시스템에서 3가지 구조적 문제 발견:

1. **Quality 이중 주입**: `_ensure_quality_tags()` fallback(L0) + `apply_style_profile_to_prompt()` prepend(외부)
2. **DB 태그 + custom_base_prompt 중복**: `_collect_character_tags()`에서 같은 태그 2번 추가
3. **레이어 소유권 규칙 부재**: 누구든 아무 레이어에 태그 삽입 → 충돌 사후 dedup 의존

## 해결

### 3-Tier 소유권 모델

| Tier | 소유자 | 레이어 | 역할 |
|------|--------|--------|------|
| **Tier 1** | StyleProfile | L0 (Quality), L11 (Atmosphere) | 화풍/품질 태그, LoRA |
| **Tier 2** | Character | L1~L6 (Subject~Accessory) | 캐릭터 외모/의상 |
| **Tier 3** | Scene | L7~L10 (Expression~Environment) | 씬 컨텍스트 |

### 핵심 변경

1. **`LAYER_OWNERS`** 상수 (`config_prompt.py`) — 각 레이어의 소유 Tier 정의
2. **Quality 태그 L0 직접 주입** — `compose_for_character(quality_tags=)` 파라미터로 StyleProfile quality를 L0에 배치, `apply_style_profile_to_prompt(skip_quality=True)`로 외부 prepend 차단
3. **`_collect_character_tags()` 중복 제거** — DB 태그 먼저 수집 → `seen_names` set 구성 → custom_base_prompt에서 동일 태그 skip, 같은 group이면 custom이 DB 대체

## 영향 범위

| 파일 | 변경 |
|------|------|
| `config_prompt.py` | `LAYER_OWNERS` 상수 추가 |
| `composition.py` | `_collect_character_tags` 중복 제거, `quality_tags` 파라미터 추가 |
| `generation_style.py` | `skip_quality` 플래그 추가 |
| `image_generation_core.py` | `skip_quality=True` + `quality_tags` 전달 |

## 테스트

- `TestQualityTagsL0Injection`: 5개 테스트
- `TestCollectCharacterTagsDedup`: 2개 테스트
- 기존 190개 테스트 전체 PASSED
