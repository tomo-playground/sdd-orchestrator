"""V3 Prompt Composition constants extracted from config.py.

가중치, 태그셋, 마커 상수를 분리하여 config.py 파일 크기를 400줄 이하로 유지한다.
"""

from __future__ import annotations

# --- V3 Prompt Composition Weights ---
PERMANENT_IDENTITY_WEIGHT_BOOST = 1.15
PERMANENT_DETAIL_WEIGHT_BOOST = 1.1
FALLBACK_STYLE_LORA_WEIGHT_MAX = 0.5
NON_FRONTAL_GAZE_WEIGHT = 1.25
EXPRESSION_ACTION_WEIGHT_BOOST = 1.2
ENVIRONMENT_WEIGHT_BOOST = 1.15
MALE_GENDER_BOOST_WEIGHT = 1.3
MALE_FOCUS_WEIGHT = 1.2
BISHOUNEN_WEIGHT = 1.1

# --- Valence (emotion polarity) ---
VALID_VALENCES: frozenset[str] = frozenset({"positive", "negative", "neutral"})

# --- V3 Prompt Composition Tags ---
BACKGROUND_SCENE_MARKER = "no_humans"
GENERIC_LOCATION_TAGS: frozenset[str] = frozenset({"indoors", "outdoors"})

NON_FRONTAL_GAZE_TAGS: frozenset[str] = frozenset(
    {
        "looking_away",
        "looking_back",
        "looking_down",
        "looking_up",
        "looking_to_the_side",
        "looking_afar",
        "looking_ahead",
        "sideways_glance",
        "averting_eyes",
        "averted_gaze",
        "downcast_eyes",
        "closed_eyes",
        "eyes_closed",
        "half-closed_eyes",
    }
)
CHARACTER_CAMERA_TAGS: frozenset[str] = frozenset(
    {
        "cowboy_shot",
        "upper_body",
        "portrait",
        "close-up",
        "close_up",
        "full_body",
        "headshot",
        "face",
        "from_waist",
    }
)
EXCLUSIVE_TAG_GROUPS: frozenset[str] = frozenset(
    {
        "hair_color",
        "eye_color",
        "hair_length",
        "skin_color",
    }
)

OUTDOOR_LOCATION_TAGS: frozenset[str] = frozenset(
    {
        "outdoors",
        "street",
        "park",
        "forest",
        "beach",
        "mountain",
        "garden",
        "city",
        "field",
        "lake",
        "river",
        "rooftop",
    }
)
INDOOR_LOCATION_TAGS: frozenset[str] = frozenset(
    {
        "indoors",
        "bedroom",
        "kitchen",
        "bathroom",
        "classroom",
        "library",
        "office",
        "cafe",
        "school",
        "hospital",
        "church",
        "restaurant",
        "shop",
        "hallway",
        "living_room",
        "stage",
    }
)
CAMERA_FRAMING_WIDE: frozenset[str] = frozenset({"full_body", "wide_shot"})
CAMERA_FRAMING_MID: frozenset[str] = frozenset({"cowboy_shot", "upper_body", "from_waist"})
CAMERA_FRAMING_CLOSE: frozenset[str] = frozenset(
    {
        "close-up",
        "close_up",
        "portrait",
        "face",
        "headshot",
    }
)
MALE_INDICATORS: frozenset[str] = frozenset({"1boy", "2boys", "3boys", "male", "man", "boy"})
FEMALE_INDICATORS: frozenset[str] = frozenset({"1girl", "2girls", "3girls", "female", "woman", "girl"})
REFERENCE_ENV_TAGS: list[str] = [
    "(white_background:1.8)",
    "(simple_background:1.5)",
    "plain_background",
    "solid_background",
    "no_shadow",
]
REFERENCE_CAMERA_TAGS: list[str] = [
    "(solo:1.5)",
    "full_body",
    "(standing:1.2)",
    "looking_at_viewer",
    "front_view",
    "straight_on",
]
