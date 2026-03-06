"""Tests for casting_sync: cascade casting changes to scenes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from services.characters.casting_sync import (
    cascade_casting_to_scenes,
    ensure_dialogue_speakers_in_db,
    swap_character_in_prompt,
)

# ---------------------------------------------------------------------------
# swap_character_in_prompt
# ---------------------------------------------------------------------------


class TestSwapCharacterInPrompt:
    """Unit tests for LoRA/trigger word swap in image_prompt."""

    OLD_LORAS = [
        {
            "name": "Usagi_Drop_-_Nitani_Yukari",
            "weight": 0.7,
            "lora_type": "character",
            "trigger_words": ["udyukari"],
        }
    ]

    NEW_LORAS = [
        {
            "name": "MHA_Midoriya",
            "weight": 0.65,
            "lora_type": "character",
            "trigger_words": ["midoriya_izuku"],
        }
    ]

    def test_swap_lora_and_trigger(self):
        prompt = (
            "<lora:Usagi_Drop_-_Nitani_Yukari:0.7>, <lora:flat_color:0.4>, masterpiece, udyukari, brown_hair, smile"
        )
        result = swap_character_in_prompt(prompt, self.OLD_LORAS, self.NEW_LORAS)

        assert "<lora:Usagi_Drop_-_Nitani_Yukari:0.7>" not in result
        assert "udyukari" not in result
        assert "<lora:MHA_Midoriya:0.65>" in result
        assert "midoriya_izuku" in result
        # Style LoRA preserved
        assert "<lora:flat_color:0.4>" in result
        assert "masterpiece" in result

    def test_remove_lora_no_replacement(self):
        """Old character has LoRA, new character has none."""
        prompt = "<lora:Usagi_Drop_-_Nitani_Yukari:0.7>, masterpiece, udyukari, smile"
        result = swap_character_in_prompt(prompt, self.OLD_LORAS, [])

        assert "<lora:Usagi_Drop_-_Nitani_Yukari:0.7>" not in result
        assert "udyukari" not in result
        assert "masterpiece" in result
        assert "smile" in result

    def test_add_lora_no_old(self):
        """Old character has no LoRA, new character has one."""
        prompt = "masterpiece, brown_hair, smile"
        result = swap_character_in_prompt(prompt, [], self.NEW_LORAS)

        assert "<lora:MHA_Midoriya:0.65>" in result
        assert "midoriya_izuku" in result
        assert "masterpiece" in result

    def test_no_change_when_both_empty(self):
        prompt = "masterpiece, smile"
        result = swap_character_in_prompt(prompt, [], [])
        assert result == prompt

    def test_empty_prompt(self):
        assert swap_character_in_prompt("", self.OLD_LORAS, self.NEW_LORAS) == ""

    def test_trigger_with_weight_stripped(self):
        """Trigger word with SD weight like (udyukari:1.15) should be removed."""
        prompt = "<lora:Usagi_Drop_-_Nitani_Yukari:0.7>, (udyukari:1.15), smile"
        result = swap_character_in_prompt(prompt, self.OLD_LORAS, [])

        assert "udyukari" not in result
        assert "smile" in result

    def test_style_lora_in_new_skipped(self):
        """Style-type LoRAs in new character should not be injected."""
        style_lora = [{"name": "shinkai", "weight": 1.0, "lora_type": "style", "trigger_words": []}]
        prompt = "masterpiece, smile"
        result = swap_character_in_prompt(prompt, [], style_lora)

        assert "<lora:shinkai" not in result

    def test_preserves_non_character_lora_order(self):
        """Style LoRAs should remain in their original position."""
        prompt = (
            "<lora:Usagi_Drop_-_Nitani_Yukari:0.7>, <lora:flat_color:0.4>, "
            "<lora:add_detail:0.3>, masterpiece, udyukari, smile"
        )
        result = swap_character_in_prompt(prompt, self.OLD_LORAS, self.NEW_LORAS)
        tokens = [t.strip() for t in result.split(",")]

        # New LoRA should be near existing LoRAs (not at the end)
        lora_positions = [i for i, t in enumerate(tokens) if "<lora:" in t]
        non_lora_start = next(i for i, t in enumerate(tokens) if "<lora:" not in t)
        assert all(p < non_lora_start for p in lora_positions)


# ---------------------------------------------------------------------------
# cascade_casting_to_scenes (integration with mocked DB)
# ---------------------------------------------------------------------------


class TestCascadeCastingToScenes:
    """Integration tests for cascade_casting_to_scenes."""

    @pytest.fixture()
    def mock_db(self):
        return MagicMock()

    @pytest.fixture()
    def old_char(self):
        char = MagicMock()
        char.id = 19
        char.loras = [
            {"name": "Usagi_Drop", "weight": 0.7, "lora_type": "character", "trigger_words": ["udyukari"]},
        ]
        return char

    @pytest.fixture()
    def new_char(self):
        char = MagicMock()
        char.id = 8
        char.loras = []
        return char

    @pytest.fixture()
    def scene_a(self):
        scene = MagicMock()
        scene.id = 100
        scene.speaker = "A"
        scene.image_prompt = "<lora:Usagi_Drop:0.7>, masterpiece, udyukari, smile"
        return scene

    @pytest.fixture()
    def scene_b(self):
        scene = MagicMock()
        scene.id = 101
        scene.speaker = "B"
        scene.image_prompt = "masterpiece, solo, smile"
        return scene

    def test_no_change_when_same_mapping(self, mock_db):
        result = cascade_casting_to_scenes(1, {"A": 8}, {"A": 8}, mock_db)
        assert result == 0

    def test_no_change_when_old_empty(self, mock_db):
        result = cascade_casting_to_scenes(1, {}, {"A": 8}, mock_db)
        assert result == 0

    @patch("services.characters.casting_sync.Session")
    def test_remaps_character_actions_and_prompt(self, _session, mock_db, old_char, new_char, scene_a, scene_b):
        # Setup DB mocks
        char_query = MagicMock()
        char_query.filter.return_value.all.return_value = [old_char, new_char]

        scene_query = MagicMock()
        scene_query.filter.return_value.all.return_value = [scene_a, scene_b]

        sca_query = MagicMock()
        sca_query.filter.return_value.update.return_value = 3

        def query_side_effect(model):
            name = getattr(model, "__name__", "") or getattr(model, "__tablename__", "")
            if "Character" in str(name) or "Character" in str(model):
                return char_query
            if "Scene" in str(name) or "Scene" in str(model):
                return scene_query
            return sca_query

        mock_db.query.side_effect = query_side_effect

        result = cascade_casting_to_scenes(
            storyboard_id=1,
            old_map={"A": 19},
            new_map={"A": 8},
            db=mock_db,
        )

        # scene_a (speaker=A) should be updated
        assert result == 1
        # LoRA should be removed from scene_a's prompt
        assert "<lora:Usagi_Drop:0.7>" not in scene_a.image_prompt
        assert "udyukari" not in scene_a.image_prompt
        # scene_b (speaker=B) should NOT be touched
        assert scene_b.image_prompt == "masterpiece, solo, smile"

    @patch("services.characters.casting_sync.Session")
    def test_both_speakers_changed(self, _session, mock_db):
        old_a = MagicMock(
            id=19, loras=[{"name": "OldA", "weight": 0.5, "lora_type": "character", "trigger_words": ["old_a_trigger"]}]
        )
        new_a = MagicMock(id=8, loras=[])
        old_b = MagicMock(id=20, loras=[])
        new_b = MagicMock(
            id=12, loras=[{"name": "NewB", "weight": 0.6, "lora_type": "character", "trigger_words": ["new_b_trigger"]}]
        )

        scene1 = MagicMock(id=100, speaker="A", image_prompt="<lora:OldA:0.5>, old_a_trigger, smile")
        scene2 = MagicMock(id=101, speaker="B", image_prompt="masterpiece, smile")

        char_q = MagicMock()
        char_q.filter.return_value.all.return_value = [old_a, new_a, old_b, new_b]
        scene_q = MagicMock()
        scene_q.filter.return_value.all.return_value = [scene1, scene2]
        sca_q = MagicMock()
        sca_q.filter.return_value.update.return_value = 1

        def side_effect(model):
            name = str(model)
            if "Character" in name:
                return char_q
            if "Scene" in name and "Action" not in name:
                return scene_q
            return sca_q

        mock_db.query.side_effect = side_effect

        result = cascade_casting_to_scenes(
            storyboard_id=1,
            old_map={"A": 19, "B": 20},
            new_map={"A": 8, "B": 12},
            db=mock_db,
        )

        assert result == 2
        # A's old LoRA removed
        assert "<lora:OldA:0.5>" not in scene1.image_prompt
        assert "old_a_trigger" not in scene1.image_prompt
        # B's new LoRA added
        assert "<lora:NewB:0.6>" in scene2.image_prompt
        assert "new_b_trigger" in scene2.image_prompt


# ---------------------------------------------------------------------------
# ensure_dialogue_speakers_in_db
# ---------------------------------------------------------------------------


class TestEnsureDialogueSpeakersInDb:
    """Tests for speaker alternation fix in DB scenes."""

    @pytest.fixture()
    def mock_db(self):
        return MagicMock()

    def _make_scenes(self, speakers: list[str]) -> list[MagicMock]:
        scenes = []
        for i, sp in enumerate(speakers):
            s = MagicMock()
            s.speaker = sp
            s.order = i
            scenes.append(s)
        return scenes

    def test_all_a_fixed_to_alternation(self, mock_db):
        scenes = self._make_scenes(["A", "A", "A", "A"])
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = scenes

        result = ensure_dialogue_speakers_in_db(1, mock_db)

        assert result == 2  # scenes[1] and scenes[3] changed to B
        assert [s.speaker for s in scenes] == ["A", "B", "A", "B"]

    def test_already_alternating_no_change(self, mock_db):
        scenes = self._make_scenes(["A", "B", "A", "B"])
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = scenes

        result = ensure_dialogue_speakers_in_db(1, mock_db)
        assert result == 0

    def test_with_narrator_scenes(self, mock_db):
        scenes = self._make_scenes(["Narrator", "A", "A", "A"])
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = scenes

        result = ensure_dialogue_speakers_in_db(1, mock_db)

        # Narrator stays, non-narrator alternate A/B
        assert scenes[0].speaker == "Narrator"
        assert scenes[1].speaker == "A"
        assert scenes[2].speaker == "B"
        assert scenes[3].speaker == "A"

    def test_empty_scenes(self, mock_db):
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        assert ensure_dialogue_speakers_in_db(1, mock_db) == 0
