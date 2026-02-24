"""Tests for Phase 16-D Cross-Scene Consistency."""

from unittest.mock import MagicMock

from services.consistency import (
    ConsistencyResult,
    GroupDrift,
    compute_group_drift,
    compute_scene_drift,
    compute_storyboard_consistency,
)

# ============================================================
# D-1: extract_identity_signature
# ============================================================


class TestExtractIdentitySignature:
    def test_basic_extraction(self):
        """WD14 태그에서 identity 그룹별 signature 추출."""
        from services.identity_score import extract_identity_signature

        wd14_tags = [
            {"tag": "black_hair", "score": 0.92, "category": "0"},
            {"tag": "blue_eyes", "score": 0.85, "category": "0"},
            {"tag": "smile", "score": 0.70, "category": "0"},
        ]

        # Mock DB query
        db = MagicMock()
        mock_row_hair = MagicMock(name="black_hair", group_name="hair_color")
        mock_row_hair.name = "black_hair"
        mock_row_hair.group_name = "hair_color"
        mock_row_eyes = MagicMock(name="blue_eyes", group_name="eye_color")
        mock_row_eyes.name = "blue_eyes"
        mock_row_eyes.group_name = "eye_color"

        db.query.return_value.filter.return_value.all.return_value = [mock_row_hair, mock_row_eyes]

        result = extract_identity_signature(wd14_tags, db)

        assert "hair_color" in result
        assert "eye_color" in result
        assert "black_hair" in result["hair_color"]
        assert "blue_eyes" in result["eye_color"]

    def test_empty_tags(self):
        """빈 WD14 결과는 모든 그룹이 빈 리스트."""
        from services.identity_score import extract_identity_signature

        db = MagicMock()
        result = extract_identity_signature([], db)

        from config import IDENTITY_SCORE_GROUPS

        for group in IDENTITY_SCORE_GROUPS:
            assert result[group] == []

    def test_threshold_filtering(self):
        """threshold 미만 태그는 제외."""
        from services.identity_score import extract_identity_signature

        wd14_tags = [
            {"tag": "black_hair", "score": 0.10, "category": "0"},  # below threshold
        ]

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []

        result = extract_identity_signature(wd14_tags, db, threshold=0.35)
        assert result["hair_color"] == []


# ============================================================
# D-2: compute_group_drift
# ============================================================


class TestComputeGroupDrift:
    def test_match(self):
        drift = compute_group_drift("hair_color", ["black_hair"], ["black_hair"])
        assert drift["status"] == "match"
        assert drift["weight"] == 1.0

    def test_mismatch(self):
        drift = compute_group_drift("hair_color", ["black_hair"], ["brown_hair"])
        assert drift["status"] == "mismatch"

    def test_missing(self):
        drift = compute_group_drift("eye_color", ["blue_eyes"], [])
        assert drift["status"] == "missing"

    def test_extra(self):
        drift = compute_group_drift("hair_style", [], ["ponytail"])
        assert drift["status"] == "extra"

    def test_no_data(self):
        drift = compute_group_drift("skin_color", [], [])
        assert drift["status"] == "no_data"

    def test_partial_overlap_is_match(self):
        """baseline과 detected에 하나라도 교집합 있으면 match."""
        drift = compute_group_drift(
            "hair_color",
            ["black_hair", "streaked_hair"],
            ["black_hair", "brown_hair"],
        )
        assert drift["status"] == "match"


# ============================================================
# D-2: compute_scene_drift
# ============================================================


class TestComputeSceneDrift:
    def test_perfect_match(self):
        baseline = {"hair_color": ["black_hair"], "eye_color": ["blue_eyes"]}
        signature = {"hair_color": ["black_hair"], "eye_color": ["blue_eyes"]}
        drift_score, groups = compute_scene_drift(baseline, signature)
        assert drift_score == 0.0
        for g in groups:
            if g["group"] in ("hair_color", "eye_color"):
                assert g["status"] == "match"

    def test_total_mismatch(self):
        baseline = {"hair_color": ["black_hair"], "eye_color": ["blue_eyes"]}
        signature = {"hair_color": ["brown_hair"], "eye_color": ["green_eyes"]}
        drift_score, groups = compute_scene_drift(baseline, signature)
        assert drift_score > 0.0

    def test_empty_baseline_and_signature(self):
        baseline = {}
        signature = {}
        drift_score, groups = compute_scene_drift(baseline, signature)
        assert drift_score == 0.0

    def test_weighted_calculation(self):
        """hair_color(1.0) mismatch + eye_color(0.8) match → drift < 1.0."""
        baseline = {"hair_color": ["black_hair"], "eye_color": ["blue_eyes"]}
        signature = {"hair_color": ["brown_hair"], "eye_color": ["blue_eyes"]}
        drift_score, _ = compute_scene_drift(baseline, signature)
        # hair_color weight 1.0 drifted, eye_color weight 0.8 matched
        # drift = 1.0 / (1.0 + 0.8) ≈ 0.556
        assert 0.5 < drift_score < 0.6

    def test_extra_has_half_penalty(self):
        """baseline 없지만 detected 있으면 0.5 * weight 패널티."""
        baseline = {"hair_color": [], "eye_color": []}
        signature = {"hair_color": ["black_hair"], "eye_color": []}
        drift_score, _ = compute_scene_drift(baseline, signature)
        # hair_color: extra → 0.5 * 1.0 = 0.5 / 1.0 = 0.5
        assert 0.4 < drift_score < 0.6


# ============================================================
# D-2: compute_storyboard_consistency (integration)
# ============================================================


class TestComputeStoryboardConsistency:
    def _mock_db(self, storyboard_exists=True, speakers=None, scenes=None, quality_scores=None):
        db = MagicMock()

        # Storyboard query
        sb_query = MagicMock()
        if storyboard_exists:
            sb_mock = MagicMock()
            sb_mock.id = 1
            sb_query.filter.return_value.first.return_value = sb_mock
        else:
            sb_query.filter.return_value.first.return_value = None

        # Track query calls
        query_calls = []

        def mock_query(*models):
            query_calls.append(models)

            from models.storyboard import Storyboard
            from models.storyboard_character import StoryboardCharacter

            if models and models[0] is Storyboard:
                return sb_query
            if models and models[0] is StoryboardCharacter:
                sc_mock = MagicMock()
                sc_list = []
                for speaker, char_id in (speakers or {}).items():
                    sc_item = MagicMock()
                    sc_item.speaker = speaker
                    sc_item.character_id = char_id
                    sc_list.append(sc_item)
                sc_mock.filter.return_value.all.return_value = sc_list
                return sc_mock

            # Default mock for Tag queries
            return MagicMock()

        db.query = mock_query
        return db

    def test_nonexistent_storyboard(self):
        db = self._mock_db(storyboard_exists=False)
        result = compute_storyboard_consistency(999, db)
        assert result["overall_consistency"] == 1.0
        assert result["scenes"] == []

    def test_no_speakers(self):
        db = self._mock_db(storyboard_exists=True, speakers={})
        result = compute_storyboard_consistency(1, db)
        assert result["overall_consistency"] == 1.0
        assert result["scenes"] == []


# ============================================================
# D-3: API response schema
# ============================================================


class TestConsistencySchemas:
    def test_group_drift_response(self):
        from schemas import GroupDriftResponse

        data = GroupDriftResponse(
            group="hair_color",
            baseline_tags=["black_hair"],
            detected_tags=["black_hair"],
            status="match",
            weight=1.0,
        )
        assert data.status == "match"
        assert data.weight == 1.0

    def test_scene_drift_response(self):
        from schemas import SceneDriftResponse

        data = SceneDriftResponse(
            scene_id=1,
            scene_order=0,
            character_id=5,
            identity_score=0.85,
            drift_score=0.15,
            groups=[],
        )
        assert data.drift_score == 0.15

    def test_consistency_response(self):
        from schemas import ConsistencyResponse

        data = ConsistencyResponse(
            storyboard_id=42,
            overall_consistency=0.85,
            scenes=[],
        )
        assert data.overall_consistency == 0.85


# ============================================================
# D-2: GroupDrift / SceneDrift TypedDict sanity
# ============================================================


class TestTypedDicts:
    def test_group_drift_keys(self):
        drift: GroupDrift = {
            "group": "hair_color",
            "baseline_tags": ["black_hair"],
            "detected_tags": ["black_hair"],
            "status": "match",
            "weight": 1.0,
        }
        assert drift["status"] == "match"

    def test_consistency_result_keys(self):
        result: ConsistencyResult = {
            "storyboard_id": 1,
            "overall_consistency": 0.95,
            "scenes": [],
        }
        assert result["overall_consistency"] == 0.95
