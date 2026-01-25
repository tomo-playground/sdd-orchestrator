"""Test cases for keyword category suggestion.

Validates that suggest_category_for_tag correctly categorizes tags
and prevents misclassification bugs from recurring.
"""

import pytest
from services.keywords import suggest_category_for_tag, SKIP_TAGS


class TestSkipTags:
    """Test that inappropriate/sensitive tags are correctly marked as skip."""

    @pytest.mark.parametrize("tag", [
        # Anatomy tags should be skipped
        "breasts",
        "medium breasts",
        "large breasts",
        "small breasts",
        "huge breasts",
        # Child-related tags should be skipped
        "child",
        "male child",
        "female child",
        "loli",
        "shota",
    ])
    def test_skip_tags_return_skip(self, tag: str):
        """Tags in SKIP_TAGS should return 'skip' category."""
        category, confidence = suggest_category_for_tag(tag)
        assert category == "skip", f"'{tag}' should be skip, got '{category}'"
        assert confidence == 1.0


class TestClothingCategory:
    """Test that clothing-related tags are correctly categorized."""

    @pytest.mark.parametrize("tag,expected_category", [
        # Basic clothing
        ("shirt", "clothing"),
        ("t-shirt", "clothing"),
        ("hoodie", "clothing"),
        ("dress", "clothing"),
        ("skirt", "clothing"),
        ("pants", "clothing"),
        ("shorts", "clothing"),
        # Specific clothing items (regression tests)
        ("white shorts", "clothing"),
        ("black thighhighs", "clothing"),
        ("thigh strap", "clothing"),
        ("off shoulder", "clothing"),
        ("one-piece swimsuit", "clothing"),
        ("swimsuit", "clothing"),
        ("bikini", "clothing"),
        ("green hoodie", "clothing"),
        ("black tank top", "clothing"),
        ("brown footwear", "clothing"),
        ("puffy sleeves", "clothing"),
        ("jewelry", "clothing"),
        ("garter", "clothing"),
        # Legwear
        ("thighhighs", "clothing"),
        ("stockings", "clothing"),
        ("pantyhose", "clothing"),
    ])
    def test_clothing_tags(self, tag: str, expected_category: str):
        """Clothing items should be categorized as clothing."""
        category, confidence = suggest_category_for_tag(tag)
        assert category == expected_category, \
            f"'{tag}' should be '{expected_category}', got '{category}'"
        assert confidence >= 0.9


class TestHairCategory:
    """Test that hair-related tags are correctly categorized."""

    @pytest.mark.parametrize("tag,expected_category", [
        # Hair colors
        ("blue hair", "hair_color"),
        ("blonde hair", "hair_color"),
        ("black hair", "hair_color"),
        # Hair lengths
        ("long hair", "hair_length"),
        ("short hair", "hair_length"),
        ("medium hair", "hair_length"),
        # Hair styles (regression tests)
        ("spiked hair", "hair_style"),
        ("spiky hair", "hair_style"),
        ("ponytail", "hair_style"),
        ("twintails", "hair_style"),
        ("bangs", "hair_style"),
        ("messy hair", "hair_style"),
        # Hair accessories
        ("hairclip", "hair_accessory"),
        ("hairpin", "hair_accessory"),
        ("hair ribbon", "hair_accessory"),
    ])
    def test_hair_tags(self, tag: str, expected_category: str):
        """Hair tags should be categorized correctly."""
        category, confidence = suggest_category_for_tag(tag)
        assert category == expected_category, \
            f"'{tag}' should be '{expected_category}', got '{category}'"
        assert confidence >= 0.9


class TestEnvironmentCategory:
    """Test that environment/location tags are correctly categorized."""

    @pytest.mark.parametrize("tag,expected_category", [
        # Indoor locations
        ("classroom", "location_indoor"),
        ("bedroom", "location_indoor"),
        ("library", "location_indoor"),
        ("cafe", "location_indoor"),
        # Outdoor locations
        ("beach", "location_outdoor"),
        ("forest", "location_outdoor"),
        ("park", "location_outdoor"),
        ("water", "location_outdoor"),
        ("mountainous horizon", "location_outdoor"),
        # Environment objects (props)
        ("shelf", "environment"),
        ("potted plant", "environment"),
        ("computer", "environment"),
        ("monitor", "environment"),
        ("plate", "environment"),
        ("food", "environment"),
        ("tiles", "environment"),
        # Background types
        ("white background", "background_type"),
        ("simple background", "background_type"),
        ("blurry background", "background_type"),
    ])
    def test_environment_tags(self, tag: str, expected_category: str):
        """Environment tags should be categorized correctly."""
        category, confidence = suggest_category_for_tag(tag)
        assert category == expected_category, \
            f"'{tag}' should be '{expected_category}', got '{category}'"
        assert confidence >= 0.9


class TestCameraCategory:
    """Test that camera/shot tags are correctly categorized."""

    @pytest.mark.parametrize("tag,expected_category", [
        # Shot types
        ("close-up", "camera"),
        ("full body", "camera"),
        ("medium shot", "camera"),
        ("wide shot", "camera"),
        ("upper body", "camera"),
        ("cowboy shot", "camera"),
        # Angles
        ("from above", "camera"),
        ("from below", "camera"),
        ("dutch angle", "camera"),
        # Effects
        ("depth of field", "camera"),
        ("bokeh", "camera"),
    ])
    def test_camera_tags(self, tag: str, expected_category: str):
        """Camera/shot tags should be categorized correctly."""
        category, confidence = suggest_category_for_tag(tag)
        assert category == expected_category, \
            f"'{tag}' should be '{expected_category}', got '{category}'"
        assert confidence >= 0.9


class TestNoMisclassification:
    """Test that tags are NOT misclassified to wrong categories.

    These are regression tests for specific bugs found in production.
    """

    @pytest.mark.parametrize("tag,wrong_category", [
        # Clothing should NOT be classified as camera
        ("medium breasts", "camera"),  # Should be skip
        ("thigh strap", "camera"),  # Should be clothing
        ("off shoulder", "camera"),  # Should be clothing
        # Clothing should NOT be classified as background_type
        ("white shorts", "background_type"),  # Should be clothing
        ("black thighhighs", "background_type"),  # Should be clothing
        # Swimsuit should NOT be classified as gaze
        ("one-piece swimsuit", "gaze"),  # Should be clothing
        # Hair should NOT be classified as hair_accessory
        ("spiked hair", "hair_accessory"),  # Should be hair_style
        # Food should NOT be classified as action
        ("food", "action"),  # Should be environment
        # Facial hair is appearance, NOT action or camera
        ("facial hair", "action"),
        ("facial hair", "camera"),
    ])
    def test_no_misclassification(self, tag: str, wrong_category: str):
        """Ensure tags are NOT classified to known wrong categories."""
        category, _ = suggest_category_for_tag(tag)
        assert category != wrong_category, \
            f"'{tag}' should NOT be '{wrong_category}' (got '{category}')"


class TestAppearanceCategory:
    """Test that appearance-related tags are correctly categorized."""

    @pytest.mark.parametrize("tag,expected_category", [
        ("freckles", "appearance"),
        ("mole", "appearance"),
        ("tattoo", "appearance"),
        ("makeup", "appearance"),
        ("slim", "appearance"),
        ("muscular", "appearance"),
        ("abs", "appearance"),
    ])
    def test_appearance_tags(self, tag: str, expected_category: str):
        """Appearance tags should be categorized correctly."""
        category, confidence = suggest_category_for_tag(tag)
        assert category == expected_category, \
            f"'{tag}' should be '{expected_category}', got '{category}'"
        assert confidence >= 0.9


class TestExpressionCategory:
    """Test that expression tags are correctly categorized."""

    @pytest.mark.parametrize("tag,expected_category", [
        ("smile", "expression"),
        ("smiling", "expression"),
        ("crying", "expression"),
        ("angry", "expression"),
        ("blush", "expression"),
        ("open mouth", "expression"),
    ])
    def test_expression_tags(self, tag: str, expected_category: str):
        """Expression tags should be categorized correctly."""
        category, confidence = suggest_category_for_tag(tag)
        assert category == expected_category, \
            f"'{tag}' should be '{expected_category}', got '{category}'"
        assert confidence >= 0.9


class TestGazeCategory:
    """Test that gaze tags are correctly categorized."""

    @pytest.mark.parametrize("tag,expected_category", [
        ("looking at viewer", "gaze"),
        ("looking away", "gaze"),
        ("looking up", "gaze"),
        ("eyes closed", "gaze"),
        ("wink", "gaze"),
    ])
    def test_gaze_tags(self, tag: str, expected_category: str):
        """Gaze tags should be categorized correctly."""
        category, confidence = suggest_category_for_tag(tag)
        assert category == expected_category, \
            f"'{tag}' should be '{expected_category}', got '{category}'"
        assert confidence >= 0.9


class TestUnknownTags:
    """Test behavior for unknown/unmatched tags."""

    @pytest.mark.parametrize("tag", [
        "xyzabc123",
        "completely_unknown_tag",
        "random_gibberish",
    ])
    def test_unknown_tags_return_empty(self, tag: str):
        """Unknown tags should return empty category with 0 confidence."""
        category, confidence = suggest_category_for_tag(tag)
        assert category == "", f"Unknown tag '{tag}' should have empty category"
        assert confidence == 0.0
