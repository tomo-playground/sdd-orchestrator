"""Tests for Seed Anchoring service.

Covers:
- Explicit seed pass-through
- No base_seed → returns -1
- Anchored seed calculation
- generate_base_seed range validation
- set_storyboard_base_seed (auto/explicit/clear)
- Config constant exists
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestResolveSeed:
    """Test resolve_scene_seed priority logic."""

    def test_explicit_seed_passthrough(self):
        """Priority 1: explicit seed != -1 should be returned as-is."""
        from services.seed_anchoring import resolve_scene_seed

        db = MagicMock()
        result = resolve_scene_seed(requested_seed=42, storyboard_id=1, scene_order=0, db=db)
        assert result == 42

    def test_explicit_seed_zero(self):
        """seed=0 is a valid explicit seed, should pass through."""
        from services.seed_anchoring import resolve_scene_seed

        db = MagicMock()
        result = resolve_scene_seed(requested_seed=0, storyboard_id=1, scene_order=0, db=db)
        assert result == 0

    def test_no_base_seed_returns_random(self):
        """No storyboard base_seed → returns -1 (random)."""
        from services.seed_anchoring import resolve_scene_seed

        mock_sb = MagicMock()
        mock_sb.base_seed = None

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = mock_sb

        result = resolve_scene_seed(requested_seed=-1, storyboard_id=1, scene_order=0, db=db)
        assert result == -1

    def test_no_storyboard_returns_random(self):
        """storyboard_id=None → returns -1 (random)."""
        from services.seed_anchoring import resolve_scene_seed

        db = MagicMock()
        result = resolve_scene_seed(requested_seed=-1, storyboard_id=None, scene_order=0, db=db)
        assert result == -1

    def test_anchored_seed_calculation(self):
        """base_seed + order * SEED_ANCHOR_OFFSET should give deterministic seed."""
        from services.seed_anchoring import resolve_scene_seed

        mock_sb = MagicMock()
        mock_sb.base_seed = 1000

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = mock_sb

        with patch("services.seed_anchoring.SEED_ANCHOR_OFFSET", 1000):
            seed_0 = resolve_scene_seed(requested_seed=-1, storyboard_id=1, scene_order=0, db=db)
            seed_1 = resolve_scene_seed(requested_seed=-1, storyboard_id=1, scene_order=1, db=db)
            seed_2 = resolve_scene_seed(requested_seed=-1, storyboard_id=1, scene_order=2, db=db)

        assert seed_0 == 1000
        assert seed_1 == 2000
        assert seed_2 == 3000

    def test_anchored_seed_wraps_at_max(self):
        """Anchored seed should wrap at 2^31 to stay in valid SD range."""
        from services.seed_anchoring import _SEED_MAX, resolve_scene_seed

        mock_sb = MagicMock()
        mock_sb.base_seed = _SEED_MAX - 500

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = mock_sb

        with patch("services.seed_anchoring.SEED_ANCHOR_OFFSET", 1000):
            result = resolve_scene_seed(requested_seed=-1, storyboard_id=1, scene_order=1, db=db)

        # Should wrap: (max-500 + 1000) % (max+1) = 499
        assert result == 499


class TestGenerateBaseSeed:
    """Test generate_base_seed range."""

    def test_in_valid_range(self):
        """Generated seed must be between 1 and 2^31-1."""
        from services.seed_anchoring import _SEED_MAX, generate_base_seed

        for _ in range(100):
            seed = generate_base_seed()
            assert 1 <= seed <= _SEED_MAX


class TestSetStoryboardBaseSeed:
    """Test set_storyboard_base_seed with various inputs."""

    def test_auto_generate(self):
        """base_seed=None should auto-generate a valid seed."""
        from services.seed_anchoring import set_storyboard_base_seed

        mock_sb = MagicMock()
        mock_sb.base_seed = None

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = mock_sb

        set_storyboard_base_seed(1, None, db)
        assert mock_sb.base_seed is not None
        assert mock_sb.base_seed >= 1
        db.commit.assert_called_once()

    def test_explicit_seed(self):
        """base_seed=12345 should set exactly."""
        from services.seed_anchoring import set_storyboard_base_seed

        mock_sb = MagicMock()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = mock_sb

        set_storyboard_base_seed(1, 12345, db)
        assert mock_sb.base_seed == 12345

    def test_clear_seed(self):
        """base_seed=0 should clear to None."""
        from services.seed_anchoring import set_storyboard_base_seed

        mock_sb = MagicMock()
        mock_sb.base_seed = 12345
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = mock_sb

        set_storyboard_base_seed(1, 0, db)
        assert mock_sb.base_seed is None

    def test_not_found_returns_none(self):
        """Non-existent storyboard → returns None."""
        from services.seed_anchoring import set_storyboard_base_seed

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        result = set_storyboard_base_seed(999, 12345, db)
        assert result is None


class TestConfigConstants:
    """Verify config constants exist."""

    def test_seed_anchor_offset_exists(self):
        from config import SEED_ANCHOR_OFFSET

        assert isinstance(SEED_ANCHOR_OFFSET, int)
        assert SEED_ANCHOR_OFFSET > 0
