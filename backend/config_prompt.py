"""Prompt Composition constants extracted from config.py.

가중치, 태그셋, 마커 상수를 분리하여 config.py 파일 크기를 400줄 이하로 유지한다.
"""

from __future__ import annotations

# --- Prompt Composition Weights ---
PERMANENT_IDENTITY_WEIGHT_BOOST = 1.25
PERMANENT_DETAIL_WEIGHT_BOOST = 1.2
FALLBACK_STYLE_LORA_WEIGHT_MAX = 0.5
NON_FRONTAL_GAZE_WEIGHT = 1.25
EXPRESSION_ACTION_WEIGHT_BOOST = 1.2
ENVIRONMENT_WEIGHT_BOOST = 1.15
MALE_GENDER_BOOST_WEIGHT = 1.3
MALE_FOCUS_WEIGHT = 1.2
BISHOUNEN_WEIGHT = 1.1

# --- Valence (emotion polarity) ---
VALID_VALENCES: frozenset[str] = frozenset({"positive", "negative", "neutral"})

# --- Prompt Composition Tags ---
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
        "clothing",
        "accessory",
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
# --- Environment Tag → Korean Mapping (image_prompt_ko 장소 동기화용) ---
# Danbooru environment tag → (primary Korean name, additional Korean aliases for detection)
ENVIRONMENT_TAG_KO_MAP: dict[str, tuple[str, list[str]]] = {
    # Indoor
    "office": ("사무실", ["오피스"]),
    "office_lobby": ("사무실 로비", ["로비"]),
    "office_pantry": ("탕비실", []),
    "bedroom": ("침실", []),
    "kitchen": ("주방", ["부엌"]),
    "bathroom": ("욕실", ["화장실"]),
    "classroom": ("교실", []),
    "library": ("도서관", []),
    "cafe": ("카페", ["커피숍", "카페테리아"]),
    "restaurant": ("식당", ["레스토랑"]),
    "hospital": ("병원", []),
    "church": ("교회", ["성당"]),
    "school": ("학교", []),
    "shop": ("가게", ["상점", "매장"]),
    "hallway": ("복도", []),
    "living_room": ("거실", []),
    "stage": ("무대", []),
    "meeting_room": ("회의실", []),
    "conference_table": ("회의 테이블", []),
    "subway_car": ("지하철", ["전철"]),
    "train_interior": ("기차 안", ["열차"]),
    "bus_interior": ("버스 안", []),
    "elevator": ("엘리베이터", []),
    "studio": ("스튜디오", []),
    "gym": ("체육관", ["헬스장"]),
    "bar": ("술집", ["바(술집)"]),
    "convenience_store": ("편의점", []),
    "warehouse": ("창고", []),
    "prison_cell": ("감방", ["감옥"]),
    "dorm_room": ("기숙사", []),
    "attic": ("다락방", []),
    "basement": ("지하실", []),
    "laundry_room": ("세탁실", []),
    "stairwell": ("계단", []),
    "kitchenette": ("간이주방", []),
    # Outdoor
    "street": ("거리", ["길거리", "도로"]),
    "park": ("공원", []),
    "forest": ("숲", ["숲속"]),
    "beach": ("해변", ["바닷가"]),
    "mountain": ("산속", ["산꼭대기"]),
    "garden": ("정원", []),
    "city": ("도시", []),
    "field": ("들판", []),
    "lake": ("호수", []),
    "river": ("강가", ["강변"]),
    "rooftop": ("옥상", []),
    "bridge": ("다리", []),
    "alley": ("골목", ["골목길"]),
    "playground": ("놀이터", []),
    "parking_lot": ("주차장", []),
    "train_station": ("기차역", []),
    "bus_stop": ("버스 정류장", ["정류장"]),
    "airport": ("공항", []),
    "pier": ("부두", []),
    "cemetery": ("묘지", []),
}

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
ABSTRACT_BACKGROUND_TAGS: frozenset[str] = frozenset(
    {
        "simple_background",
        "white_background",
        "transparent_background",
        "black_background",
        "grey_background",
        "gradient_background",
    }
)
MALE_INDICATORS: frozenset[str] = frozenset({"1boy", "2boys", "3boys", "male", "man", "boy"})
FEMALE_INDICATORS: frozenset[str] = frozenset({"1girl", "2girls", "3girls", "female", "woman", "girl"})
REFERENCE_ENV_TAGS: list[str] = []
REFERENCE_CAMERA_TAGS: list[str] = [
    "solo",
    "upper_body",
    "looking_at_viewer",
]
# Lighting/cinematic tags injected into LAYER_ATMOSPHERE for reference images.
# Ensures reference rendering style (shading, depth) matches scene output.
REFERENCE_LIGHTING_TAGS: list[str] = [
    "soft_lighting",
    "depth_of_field",
]

# --- 12-Layer Ownership (Tier 소유권) ---
# 각 레이어를 소유하는 Tier. 소유자만 해당 레이어에 태그를 주입할 수 있다.
# Tier 1: style_profile — Quality(L0), Atmosphere(L11)
# Tier 2: character — Subject~Accessory(L1~L6)
# Tier 3: scene — Expression~Environment(L7~L10)
LAYER_OWNERS: dict[int, str] = {
    0: "style_profile",  # Quality
    1: "character",  # Subject
    2: "character",  # Identity
    3: "character",  # Body
    4: "character",  # Main Cloth
    5: "character",  # Detail Cloth
    6: "character",  # Accessory
    7: "scene",  # Expression
    8: "scene",  # Action
    9: "scene",  # Camera
    10: "scene",  # Environment
    11: "style_profile",  # Atmosphere
}
