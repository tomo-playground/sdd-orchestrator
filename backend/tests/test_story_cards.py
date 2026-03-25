"""SP-075: StoryCard 테스트 — CRUD API + 빌더 + status 전환."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

# ── Fixtures ──────────────────────────────────────────


@pytest.fixture
def sample_card(db_session):
    """미사용 소재 카드 1개 생성."""
    from models.story_card import StoryCard

    card = StoryCard(
        group_id=1,
        cluster="첫 만남",
        title="처음 만난 날의 기억",
        status="unused",
        situation="길을 걷다가 우연히 다시 만났다",
        hook_angle="운명적인 재회",
        key_moments=["시선 교환", "말을 걸기", "연락처 교환"],
        emotional_arc={"start": "설렘", "peak": "긴장", "end": "기대"},
        empathy_details=["심장이 빨라졌다", "말이 잘 안 나왔다"],
        characters_hint={"speaker_a": "수줍은 남자", "speaker_b": "활발한 여자"},
        hook_score=0.85,
    )
    db_session.add(card)
    db_session.commit()
    db_session.refresh(card)
    return card


@pytest.fixture
def sample_cards(db_session):
    """미사용 소재 카드 3개 생성."""
    from models.story_card import StoryCard

    cards = []
    for _i, (title, score) in enumerate(
        [("소재A", 0.9), ("소재B", 0.7), ("소재C", 0.8)],
    ):
        card = StoryCard(
            group_id=1,
            cluster="테스트",
            title=title,
            status="unused",
            hook_score=score,
        )
        db_session.add(card)
        cards.append(card)
    db_session.commit()
    for c in cards:
        db_session.refresh(c)
    return cards


# ── CRUD API 테스트 ─────────────────────────────────


class TestStoryCardCRUD:
    def test_create_story_card(self, client):
        resp = client.post(
            "/api/v1/groups/1/story-cards",
            json={"title": "새 소재", "cluster": "테스트"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "새 소재"
        assert data["status"] == "unused"
        assert data["group_id"] == 1

    def test_list_story_cards(self, client, sample_cards):
        resp = client.get("/api/v1/groups/1/story-cards")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        # hook_score DESC 정렬 확인
        scores = [i["hook_score"] for i in data["items"]]
        assert scores == sorted(scores, reverse=True)

    def test_list_with_status_filter(self, client, sample_card):
        resp = client.get("/api/v1/groups/1/story-cards?status=unused")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        resp = client.get("/api/v1/groups/1/story-cards?status=used")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_update_story_card(self, client, sample_card):
        resp = client.patch(
            f"/api/v1/story-cards/{sample_card.id}",
            json={"title": "수정된 제목"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "수정된 제목"

    def test_delete_story_card(self, client, sample_card):
        resp = client.delete(f"/api/v1/story-cards/{sample_card.id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        # 삭제 후 조회 → total=0
        resp = client.get("/api/v1/groups/1/story-cards")
        # sample_card만 있었으므로 0
        data = resp.json()
        # seed_default에서 다른 카드가 없으므로 sample_card가 삭제되면 0
        assert all(i["id"] != sample_card.id for i in data["items"])

    def test_get_nonexistent_group_404(self, client):
        resp = client.post(
            "/api/v1/groups/9999/story-cards",
            json={"title": "소재"},
        )
        assert resp.status_code == 404

    def test_update_deleted_card_404(self, client, sample_card, db_session):
        from sqlalchemy import func

        from models.story_card import StoryCard

        card = db_session.get(StoryCard, sample_card.id)
        card.deleted_at = func.now()
        db_session.commit()

        before_count = db_session.query(StoryCard).count()

        resp = client.patch(
            f"/api/v1/story-cards/{sample_card.id}",
            json={"title": "시도"},
        )
        assert resp.status_code == 404

        # INV-1: 삭제된 엔티티 부활 금지 — 레코드 수/삭제 상태 불변
        db_session.expire_all()
        after_count = db_session.query(StoryCard).count()
        assert after_count == before_count
        card_after = db_session.query(StoryCard).filter_by(id=sample_card.id).one_or_none()
        assert card_after is not None
        assert card_after.deleted_at is not None

    def test_update_nonexistent_card_404(self, client, db_session):
        from models.story_card import StoryCard

        before_count = db_session.query(StoryCard).count()

        resp = client.patch(
            "/api/v1/story-cards/9999",
            json={"title": "없는 카드"},
        )
        assert resp.status_code == 404

        # INV-1: 존재하지 않는 카드 자동 생성 금지
        after_count = db_session.query(StoryCard).count()
        assert after_count == before_count


# ── Status 전환 테스트 ─────────────────────────────


class TestStoryCardStatus:
    def test_unused_to_used(self, client, sample_card):
        resp = client.patch(
            f"/api/v1/story-cards/{sample_card.id}",
            json={"status": "used"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "used"
        assert data["used_at"] is not None

    def test_used_to_unused_resets(self, client, sample_card, db_session):
        from models.story_card import StoryCard

        card = db_session.get(StoryCard, sample_card.id)
        card.status = "used"
        card.used_at = datetime.now(UTC)
        card.used_in_storyboard_id = None  # no storyboard for test
        db_session.commit()

        resp = client.patch(
            f"/api/v1/story-cards/{sample_card.id}",
            json={"status": "unused"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "unused"
        assert data["used_at"] is None
        assert data["used_in_storyboard_id"] is None

    def test_mark_cards_as_used(self, db_session, sample_cards):
        from models.storyboard import Storyboard
        from services.story_card import mark_cards_as_used

        sb = Storyboard(group_id=1, title="테스트 스토리보드")
        db_session.add(sb)
        db_session.commit()
        db_session.refresh(sb)

        card_ids = [c.id for c in sample_cards]
        updated = mark_cards_as_used(db_session, card_ids, sb.id)
        assert updated == 3

        for c in sample_cards:
            db_session.refresh(c)
            assert c.status == "used"
            assert c.used_in_storyboard_id == sb.id

    def test_already_used_idempotent(self, db_session, sample_card):
        from services.story_card import mark_cards_as_used

        sample_card.status = "used"
        db_session.commit()

        updated = mark_cards_as_used(db_session, [sample_card.id], storyboard_id=1)
        assert updated == 0


# ── 빌더 테스트 ──────────────────────────────────


class TestStoryMaterialsBuilder:
    def test_build_empty(self):
        from services.agent.prompt_builders_writer import build_story_materials_section

        assert build_story_materials_section(None) == ""
        assert build_story_materials_section([]) == ""

    def test_build_single_material(self):
        from services.agent.prompt_builders_writer import build_story_materials_section

        result = build_story_materials_section(
            [{"title": "소재1", "situation": "상황1", "hook_angle": "후크1"}],
        )
        assert "Material 1: 소재1" in result
        assert "Situation: 상황1" in result
        assert "Hook Angle: 후크1" in result

    def test_build_multiple_materials(self):
        from services.agent.prompt_builders_writer import build_story_materials_section

        materials = [
            {"title": "A", "key_moments": ["순간1", "순간2"]},
            {"title": "B", "empathy_details": ["공감1"]},
            {"title": "C", "emotional_arc": {"start": "호기심", "end": "감동"}},
        ]
        result = build_story_materials_section(materials)
        assert "Material 1: A" in result
        assert "Material 2: B" in result
        assert "Material 3: C" in result
        assert "Key Moments:" in result
        assert "Empathy Details:" in result
        assert "Emotional Arc:" in result


# ── Gemini 소재 생성 테스트 ───────────────────────


class TestStoryCardGenerate:
    def test_generate_story_cards(self, client, db_session):
        import services.llm.registry as reg

        mock_response = AsyncMock()
        mock_response.text = """[{
            "title": "생성된 소재",
            "situation": "AI 생성 상황",
            "hook_angle": "AI 후크",
            "key_moments": ["장면1"],
            "emotional_arc": {"start": "호기심", "peak": "놀람", "end": "감동"},
            "empathy_details": ["공감1"],
            "characters_hint": {"speaker_a": "A"},
            "hook_score": 0.75
        }]"""

        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(return_value=mock_response)

        saved = reg._provider
        reg._provider = mock_provider
        try:
            resp = client.post(
                "/api/v1/groups/1/story-cards/generate",
                json={"cluster": "테스트", "count": 1},
            )
        finally:
            reg._provider = saved
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "생성된 소재"
        assert data[0]["status"] == "unused"

    def test_generate_invalid_json(self, client, db_session):
        import services.llm.registry as reg

        mock_response = AsyncMock()
        mock_response.text = "이것은 JSON이 아닙니다"

        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(return_value=mock_response)

        saved = reg._provider
        reg._provider = mock_provider
        try:
            resp = client.post(
                "/api/v1/groups/1/story-cards/generate",
                json={"cluster": "테스트", "count": 3},
            )
        finally:
            reg._provider = saved
        assert resp.status_code == 400


# ── Research 소재 주입 테스트 ─────────────────────


class TestResearchStoryCards:
    def test_get_story_cards_tool(self, db_session, sample_cards):
        """소재 카드 도구가 미사용 카드를 반환하는지 확인."""
        import asyncio

        from services.agent.tools.research_tools import create_research_executors

        state: dict = {}
        mock_store = AsyncMock()
        executors = create_research_executors(mock_store, db_session, state)

        result = asyncio.run(executors["get_story_cards"](group_id=1))
        assert "소재A" in result
        assert "소재B" in result
        assert "소재C" in result
        assert state.get("used_story_card_ids") is not None
        assert len(state["used_story_card_ids"]) == 3

    def test_get_story_cards_no_materials(self, db_session):
        """소재가 없을 때 적절한 메시지 반환."""
        import asyncio

        from services.agent.tools.research_tools import create_research_executors

        state: dict = {}
        mock_store = AsyncMock()
        executors = create_research_executors(mock_store, db_session, state)

        result = asyncio.run(executors["get_story_cards"](group_id=1))
        assert "소재 없음" in result
