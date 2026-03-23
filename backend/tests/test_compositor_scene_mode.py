"""Compositor scene_mode 관련 테스트 — SP-059."""

from __future__ import annotations

from services.agent.nodes._cine_compositor import _OUTPUT_FORMAT, _build_prompt
from services.agent.prompt_builders_c import (
    _resolve_subject_example,
    build_compositor_multi_rules,
)

# --- build_compositor_multi_rules ---


def test_build_compositor_multi_rules_true():
    result = build_compositor_multi_rules(True)
    assert "scene_mode" in result
    assert "Multi-Character" in result
    assert len(result) > 0


def test_build_compositor_multi_rules_false():
    result = build_compositor_multi_rules(False)
    assert result == ""


def test_build_compositor_multi_rules_no_gender():
    result = build_compositor_multi_rules(True, char_a_ctx=None, char_b_ctx=None)
    # 성별 정보 없으면 subject 예시 라인 자체가 생략됨 (Danbooru 위반 방지)
    assert "subject should reflect" not in result
    assert "Multi-Character" in result  # 기본 규칙은 여전히 포함


def test_build_compositor_multi_rules_with_gender():
    result = build_compositor_multi_rules(
        True,
        char_a_ctx={"gender": "male"},
        char_b_ctx={"gender": "female"},
    )
    assert "1boy, 1girl" in result


# --- _resolve_subject_example ---


def test_resolve_subject_male_male():
    assert _resolve_subject_example({"gender": "male"}, {"gender": "male"}) == "2boys"


def test_resolve_subject_female_female():
    assert _resolve_subject_example({"gender": "female"}, {"gender": "female"}) == "2girls"


def test_resolve_subject_mixed():
    assert _resolve_subject_example({"gender": "male"}, {"gender": "female"}) == "1boy, 1girl"


def test_resolve_subject_none():
    assert _resolve_subject_example(None, None) == ""


# --- _OUTPUT_FORMAT ---


def test_output_format_has_scene_mode():
    assert "scene_mode" in _OUTPUT_FORMAT


# --- _build_prompt with multi rules ---


def test_multi_rules_injected_when_multi():
    multi_block = build_compositor_multi_rules(True)
    prompt = _build_prompt(
        "[]",
        {},
        {},
        {},
        "",
        "",
        "",
        "",
        multi_rules_block=multi_block,
    )
    assert "Multi-Character" in prompt


def test_multi_rules_absent_when_not_multi():
    prompt = _build_prompt(
        "[]",
        {},
        {},
        {},
        "",
        "",
        "",
        "",
        multi_rules_block="",
    )
    assert "Multi-Character" not in prompt


# --- single fallback output format ---


def test_single_fallback_output_has_scene_mode():
    from services.agent.nodes.cinematographer import _JSON_OUTPUT_INSTRUCTION

    assert "scene_mode" in _JSON_OUTPUT_INSTRUCTION
