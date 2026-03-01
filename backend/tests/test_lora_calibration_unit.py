"""lora_calibration 순수 함수 단위 테스트."""

from __future__ import annotations

from services.lora_calibration import get_effective_weight


class TestGetEffectiveWeight:
    def test_optimal_weight_priority(self):
        lora = {"optimal_weight": 0.65, "default_weight": 0.8}
        assert get_effective_weight(lora) == 0.65

    def test_default_weight_fallback(self):
        lora = {"optimal_weight": None, "default_weight": 0.8}
        assert get_effective_weight(lora) == 0.8

    def test_hardcoded_fallback(self):
        lora = {"optimal_weight": None, "default_weight": None}
        assert get_effective_weight(lora) == 0.7

    def test_no_keys_fallback(self):
        assert get_effective_weight({}) == 0.7

    def test_zero_optimal_weight(self):
        lora = {"optimal_weight": 0.0, "default_weight": 0.5}
        # 0.0 is falsy but not None, so it should be used
        assert get_effective_weight(lora) == 0.0

    def test_string_weight_coerced(self):
        lora = {"optimal_weight": "0.5"}
        assert get_effective_weight(lora) == 0.5
