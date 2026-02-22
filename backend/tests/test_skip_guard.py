"""_skip_guard 모듈 단위 테스트."""

from services.agent.nodes._skip_guard import should_skip


def test_should_skip_research_stage():
    """research 스테이지 스킵 시 director_plan, research 노드 스킵."""
    state = {"skip_stages": ["research"]}
    assert should_skip(state, "director_plan") is True
    assert should_skip(state, "research") is True
    assert should_skip(state, "critic") is False


def test_should_skip_concept_stage():
    """concept 스테이지 스킵 시 critic, concept_gate 노드 스킵."""
    state = {"skip_stages": ["concept"]}
    assert should_skip(state, "critic") is True
    assert should_skip(state, "concept_gate") is True
    assert should_skip(state, "writer") is False


def test_should_skip_production_stage():
    """production 스테이지 스킵 시 7개 노드 모두 스킵."""
    state = {"skip_stages": ["production"]}
    for node in [
        "director_checkpoint",
        "cinematographer",
        "tts_designer",
        "sound_designer",
        "copyright_reviewer",
        "director",
        "human_gate",
    ]:
        assert should_skip(state, node) is True
    assert should_skip(state, "finalize") is False


def test_should_skip_explain_stage():
    """explain 스테이지 스킵."""
    state = {"skip_stages": ["explain"]}
    assert should_skip(state, "explain") is True
    assert should_skip(state, "learn") is False


def test_should_skip_empty_stages():
    """skip_stages가 비어있으면 모든 노드 실행."""
    state = {"skip_stages": []}
    assert should_skip(state, "director_plan") is False
    assert should_skip(state, "cinematographer") is False


def test_should_skip_none_stages():
    """skip_stages가 None이면 모든 노드 실행."""
    state = {}
    assert should_skip(state, "director_plan") is False
    assert should_skip(state, "explain") is False


def test_should_skip_unknown_node():
    """알 수 없는 노드는 항상 False."""
    state = {"skip_stages": ["research", "concept", "production", "explain"]}
    assert should_skip(state, "writer") is False
    assert should_skip(state, "review") is False
    assert should_skip(state, "finalize") is False
    assert should_skip(state, "learn") is False


def test_should_skip_all_stages():
    """Express 프리셋: 4개 스테이지 모두 스킵."""
    state = {"skip_stages": ["research", "concept", "production", "explain"]}
    assert should_skip(state, "director_plan") is True
    assert should_skip(state, "critic") is True
    assert should_skip(state, "cinematographer") is True
    assert should_skip(state, "explain") is True
    # Core는 항상 실행
    assert should_skip(state, "writer") is False
    assert should_skip(state, "review") is False
    assert should_skip(state, "finalize") is False
    assert should_skip(state, "learn") is False
