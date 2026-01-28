"""Keyword management service.

Handles keyword normalization, synonyms, categories, and suggestions.
All keyword data is sourced from PostgreSQL database (tags, synonyms tables).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from config import CACHE_DIR, logger

# --- Lazy imports for circular dependency avoidance ---
_split_prompt_tokens = None
_normalize_prompt_tokens = None


def _get_cache_dir() -> Path:
    return CACHE_DIR


def _get_logger():
    return logger


def _get_split_prompt_tokens():
    global _split_prompt_tokens
    if _split_prompt_tokens is None:
        from services.prompt import split_prompt_tokens
        _split_prompt_tokens = split_prompt_tokens
    return _split_prompt_tokens


def _get_normalize_prompt_tokens():
    global _normalize_prompt_tokens
    if _normalize_prompt_tokens is None:
        from services.prompt import normalize_prompt_tokens
        _normalize_prompt_tokens = normalize_prompt_tokens
    return _normalize_prompt_tokens


# --- Ignore list (tokens to filter out from prompts) ---
# These are typically low-quality or unwanted tags
IGNORE_TOKENS = frozenset([
    "nsfw", "nude", "uncensored", "cleavage", "text", "watermark",
    "signature", "logo", "username", "artist name", "copyright",
    "low quality", "worst quality", "normal quality", "bad quality",
    "bad anatomy", "bad hands", "missing fingers", "extra digits",
    "fewer digits", "extra limbs", "cloned face", "mutated",
    "deformed", "disfigured", "ugly", "blur", "blurry",
    "jpeg artifacts", "cropped", "out of frame", "highres", "absurdres",
])

# --- Category suggestion patterns ---
# Pattern-based category detection for unknown tags
# Organized by SD Prompt Priority Order (lower priority = earlier in prompt)
CATEGORY_PATTERNS: dict[str, list[str]] = {
    # === Priority 1: Quality (맨 앞) ===
    "quality": [
        "masterpiece", "best quality", "high quality", "amazing quality",
        "very aesthetic", "absurdres", "highres", "8k", "detailed",
        "ultra detailed", "extremely detailed", "intricate details",
        "official art", "anime coloring", "perfect lighting",
    ],

    # === Priority 2: Subject ===
    "subject": [
        "1girl", "2girls", "3girls", "4girls", "5girls", "6+girls",
        "1boy", "2boys", "3boys", "4boys", "5boys", "6+boys",
        "solo", "duo", "trio", "group", "crowd", "everyone",
        "multiple girls", "multiple boys", "couple", "1other",
    ],

    # === Priority 3: Identity (LoRA triggers) ===
    # Note: Character-specific triggers are synced from loras.trigger_words via sync_lora_triggers_to_tags()
    # This pattern list is for generic identity markers only
    "identity": [
        "male", "female", "androgynous",
    ],

    # === Priority 4: Appearance ===
    "hair_color": [
        "black hair", "blonde hair", "brown hair", "red hair",
        "blue hair", "green hair", "pink hair", "purple hair",
        "white hair", "silver hair", "grey hair", "gray hair",
        "orange hair", "aqua hair", "light brown hair",
        "multicolored hair", "gradient hair", "streaked hair",
        "two-tone hair", "colored inner hair",
    ],
    "hair_length": [
        "short hair", "medium hair", "long hair", "very long hair",
        "absurdly long hair", "shoulder-length hair", "bald",
    ],
    "hair_style": [
        "bangs", "blunt bangs", "side bangs", "parted bangs", "swept bangs",
        "ponytail", "high ponytail", "low ponytail", "side ponytail",
        "twintails", "low twintails", "short twintails",
        "braid", "braided ponytail", "twin braids", "side braid", "french braid",
        "bun", "double bun", "hair bun", "side bun",
        "bob cut", "hime cut", "pixie cut", "drill hair",
        "ahoge", "antenna hair", "sidelocks", "hair over one eye",
        "hair between eyes", "hair over shoulder",
        "messy hair", "straight hair", "curly hair", "wavy hair",
        "spiked hair", "spiky hair", "slicked back hair",
    ],
    "hair_accessory": [
        "hairclip", "hairpin", "hair ornament", "hair flower",
        "hairband", "headband", "hair ribbon", "hair bow",
        "scrunchie", "hair tie", "hair stick",
        "crown", "tiara", "headpiece",
    ],
    "eye_color": [
        "blue eyes", "red eyes", "green eyes", "brown eyes",
        "purple eyes", "yellow eyes", "orange eyes", "pink eyes",
        "aqua eyes", "golden eyes", "amber eyes", "grey eyes",
        "heterochromia", "multicolored eyes", "glowing eyes",
    ],
    "skin_color": [
        "pale skin", "dark skin", "tanned skin", "tanned",
        "white skin", "brown skin", "fair skin", "light skin",
        "dark-skinned", "light-skinned",
    ],
    "body_feature": [
        "pointy ears", "elf ears", "animal ears", "cat ears", "dog ears",
        "fox ears", "rabbit ears", "wolf ears",
        "horns", "demon horns", "dragon horns",
        "wings", "angel wings", "demon wings", "fairy wings",
        "tail", "cat tail", "fox tail", "demon tail",
        "halo", "fang", "fangs",
    ],
    "appearance": [
        "freckles", "mole", "beauty mark", "scar", "tattoo",
        "piercing", "ear piercing", "facial mark",
        "makeup", "lipstick", "eyeshadow", "mascara",
        "slim", "petite", "tall", "short", "muscular", "chubby",
        "abs", "muscles",
    ],

    # === Priority 5: Clothing ===
    "clothing": [
        # Tops
        "shirt", "t-shirt", "blouse", "sweater", "hoodie",
        "jacket", "coat", "blazer", "cardigan", "vest",
        "tank top", "crop top", "tube top", "camisole",
        "black tank top", "white tank top",
        # Bottoms
        "skirt", "miniskirt", "long skirt", "pleated skirt",
        "pants", "jeans", "shorts", "leggings",
        "white shorts", "black shorts", "denim shorts",
        # Full body
        "dress", "sundress", "wedding dress", "evening dress",
        "uniform", "school uniform", "sailor uniform", "maid outfit",
        "suit", "tuxedo", "kimono", "yukata", "chinese clothes",
        "swimsuit", "one-piece swimsuit", "bikini", "school swimsuit",
        # Details
        "sleeveless", "short sleeves", "long sleeves", "wide sleeves",
        "off shoulder", "off-shoulder", "bare shoulders",
        "collar", "tie", "necktie", "bowtie", "bow",
        "button", "zipper", "pocket", "belt",
        "ribbon", "lace", "frills", "puffy sleeves",
        # Underwear/legwear
        "socks", "thighhighs", "kneehighs", "pantyhose",
        "stockings", "fishnet", "bare legs",
        "black thighhighs", "white thighhighs",
        "thigh strap", "garter", "garter belt",
        # Footwear
        "barefoot", "shoes", "boots", "sneakers", "sandals",
        "high heels", "loafers", "slippers", "mary janes",
        "footwear", "brown footwear", "black footwear", "white footwear",
        # Accessories
        "glasses", "sunglasses", "hat", "cap", "beret",
        "gloves", "scarf", "bag", "backpack", "purse",
        "earrings", "necklace", "bracelet", "ring", "choker",
        "jewelry",
        # Outerwear
        "green hoodie", "black hoodie", "white hoodie",
        # States
        "open clothes", "open jacket", "open shirt",
        "hood", "hood up", "hood down",
        "apron", "overalls", "plaid", "striped",
    ],

    # === Priority 6: Expression ===
    "expression": [
        # Basic emotions
        "smile", "smiling", "grin", "smirk", "laugh", "laughing", "happy",
        "sad", "crying", "tears", "frown", "sobbing",
        "angry", "annoyed", "frustrated", "glare",
        "surprised", "shocked", "scared", "frightened",
        "embarrassed", "shy", "blush", "blushing", "nervous",
        "serious", "expressionless", "deadpan", "stoic",
        "sleepy", "tired", "exhausted", "yawning",
        "excited", "cheerful", "joyful",
        # Mouth
        "open mouth", "closed mouth", "parted lips",
        "tongue", "tongue out", "licking lips",
        "pout", "pouting", ":o", ":d", ";)",
        # Effects
        "sweat", "sweatdrop", "nosebleed", "drool", "drooling", "teardrop",
    ],

    # === Priority 7: Gaze ===
    "gaze": [
        "looking at viewer", "looking away", "looking up", "looking down",
        "looking back", "looking to the side", "eye contact",
        "eyes closed", "closed eyes", "half-closed eyes", "squinting",
        "one eye closed", "wink", "winking",
        "staring", "glancing", "averted gaze", "downcast eyes",
        "empty eyes", "sparkling eyes", "heart-shaped pupils",
    ],

    # === Priority 8: Pose (Static) ===
    "pose": [
        # Standing/sitting
        "standing", "sitting", "kneeling", "crouching", "squatting",
        "lying", "lying down", "on back", "on stomach", "on side",
        "leaning", "leaning forward", "leaning back",
        "reclining", "lounging", "sprawling",
        # Arms
        "arms crossed", "arms behind back", "arms up", "arms at sides",
        "hand on hip", "hands on hips", "hands together",
        "hand up", "hands up", "arm up",
        "hand on chest", "hand on face", "hand on head",
        "v", "peace sign", "thumbs up",
        # Legs
        "crossed legs", "spread legs", "legs together",
        "one leg raised", "leg up",
        # General
        "profile", "from behind", "back", "turned around",
        "curled up", "fetal position",
    ],

    # === Priority 9: Action (Dynamic) ===
    "action": [
        # Movement
        "walking", "running", "jumping", "flying",
        "dancing", "stretching", "bending", "turning",
        # Hand actions (compound patterns to ensure priority over clothing "bag")
        "holding", "holding bag", "holding book", "holding cup", "holding phone",
        "holding umbrella", "holding weapon", "holding food", "holding flower",
        "holding hands", "holding sword", "holding gun", "holding knife",
        "grabbing", "reaching", "pointing", "waving",
        "hugging", "embracing", "carrying",
        # Activities
        "reading", "writing", "drawing", "typing", "using phone",
        "eating", "drinking", "cooking", "baking",
        "singing", "playing instrument", "playing guitar", "playing piano",
        "gaming", "playing game",
        "sleeping", "napping", "resting",
        "bathing", "showering", "dressing", "undressing",
        "fighting", "kicking", "punching",
        "swimming", "diving",
    ],

    # === Priority 10: Camera ===
    "camera": [
        # Shot types
        "close-up", "closeup", "extreme close-up", "face focus",
        "portrait", "bust shot", "upper body",
        "cowboy shot", "thigh focus", "hip focus",
        "full body", "medium shot", "long shot", "wide shot", "very wide shot",
        # Angles
        "from above", "from below", "from side", "from behind",
        "dutch angle", "tilted frame",
        "low angle", "high angle", "bird's eye view", "worm's eye view",
        "straight-on", "front view", "side view", "back view",
        # POV
        "pov", "first person view", "over shoulder",
        # Effects
        "depth of field", "bokeh", "motion blur", "lens flare",
        "out of frame", "cropped", "partially visible",
    ],

    # === Priority 11: Location ===
    "location_indoor": [
        "indoors", "room", "interior",
        "bedroom", "living room", "kitchen", "bathroom",
        "classroom", "library", "office", "study",
        "cafe", "restaurant", "bar", "shop", "store",
        "train", "bus", "car interior", "airplane",
        "hospital", "church", "temple", "shrine",
        "gym", "pool", "locker room",
    ],
    # === Priority 11b: Environment Objects (props in scene) ===
    "environment": [
        # Indoor props
        "shelf", "bookshelf", "desk", "table", "chair", "sofa", "couch",
        "bed", "pillow", "blanket", "curtain", "window",
        "door", "stairs", "floor", "wall", "ceiling",
        "lamp", "chandelier", "mirror",
        # Tech items
        "computer", "monitor", "keyboard", "laptop", "phone", "smartphone",
        "television", "tv", "screen",
        # Kitchen items
        "plate", "cup", "mug", "bowl", "utensils", "fork", "spoon", "knife",
        "food", "drink", "bottle", "glass",
        # Plants
        "potted plant", "flower", "plant", "vase", "flowers",
        # Tiles/textures
        "tiles", "brick", "concrete", "wood floor", "carpet",
    ],
    "location_outdoor": [
        "outdoors", "outside", "exterior",
        "street", "alley", "sidewalk", "crosswalk",
        "park", "garden", "yard", "playground",
        "forest", "woods", "jungle", "meadow", "field",
        "beach", "ocean", "sea", "lake", "river", "waterfall", "pond",
        "water",  # Generic water environment
        "mountain", "hill", "cliff", "valley",
        "mountainous horizon",
        "city", "town", "village", "rooftop", "balcony",
        "bridge", "pier", "dock",
    ],
    "background_type": [
        "simple background", "white background", "black background",
        "grey background", "gray background", "gradient background",
        "blurry background", "detailed background", "abstract background",
        "no background", "transparent background",
        "starry background", "floral background",
    ],

    # === Priority 12: Time/Weather ===
    "time_weather": [
        # Time
        "day", "daytime", "morning", "afternoon",
        "night", "nighttime", "midnight", "evening",
        "sunset", "sunrise", "dusk", "dawn", "twilight",
        "golden hour", "blue hour",
        # Weather
        "sunny", "cloudy", "overcast", "rainy", "rain",
        "snowy", "snow", "foggy", "fog", "misty",
        "stormy", "thunder", "lightning", "windy",
        # Environmental effects
        "falling leaves", "falling petals", "cherry blossoms",
        "floating particles", "dust particles", "fireflies",
        "bubbles", "sparkles", "confetti",
    ],

    # === Priority 13: Lighting ===
    "lighting": [
        "natural light", "sunlight", "moonlight", "starlight",
        "backlighting", "backlit", "rim light", "rim lighting",
        "dramatic lighting", "cinematic lighting", "studio lighting",
        "soft lighting", "harsh lighting", "ambient lighting",
        "neon lights", "neon", "glowing", "light rays",
        "shadow", "shadows", "dark", "bright",
        "warm lighting", "cold lighting", "golden light",
    ],

    # === Priority 14: Mood ===
    "mood": [
        "romantic", "melancholic", "melancholy", "peaceful", "serene",
        "tense", "dramatic", "intense", "epic",
        "mysterious", "eerie", "creepy", "horror",
        "ethereal", "magical", "fantastical", "dreamy",
        "nostalgic", "bittersweet", "wistful",
        "cozy", "comfortable", "warm", "intimate",
        "lonely", "isolated", "solitary",
        "cheerful", "bright", "happy", "joyful",
        "gloomy", "dark", "somber", "moody",
    ],

    # === Priority 15: Art Style ===
    "style": [
        "anime", "manga", "anime style", "manga style",
        "realistic", "photorealistic", "semi-realistic",
        "sketch", "lineart", "line art", "ink",
        "watercolor", "oil painting", "digital art",
        "cel shading", "flat color", "soft shading",
        "chibi", "super deformed", "kemonomimi mode",
        "monochrome", "greyscale", "sepia",
        "pixel art", "voxel", "3d",
    ],
}

# Category to SD Priority mapping (lower = earlier in prompt)
CATEGORY_PRIORITY: dict[str, int] = {
    "quality": 1,
    "subject": 2,
    "identity": 3,
    "hair_color": 4,
    "hair_length": 4,
    "hair_style": 4,
    "hair_accessory": 4,
    "eye_color": 4,
    "skin_color": 4,
    "body_feature": 4,
    "appearance": 4,
    "clothing": 5,
    "expression": 6,
    "gaze": 7,
    "pose": 8,
    "action": 9,
    "camera": 10,
    "location_indoor": 11,
    "location_outdoor": 11,
    "environment": 11,  # Indoor/outdoor props
    "background_type": 11,
    "time_weather": 12,
    "lighting": 13,
    "mood": 14,
    "style": 15,
}

# Tags to skip (not useful for prompts or sensitive)
SKIP_TAGS = frozenset([
    # Anatomy (not useful for scene prompts)
    "breasts", "large breasts", "medium breasts", "small breasts", "huge breasts",
    "collarbone", "thighs", "thick thighs", "navel", "midriff", "cleavage",
    "ass", "sideboob", "underboob", "nipples", "areolae", "crotch",
    "groin", "armpits", "bare shoulders",
    # Meta tags (handled separately)
    # Note: "male focus" removed to help reinforce male character generation
    "female focus", "solo focus", "no humans",
    "virtual youtuber", "vtuber", "commentary", "translation",
    "border", "letterboxed", "pillarboxed",
    "gradient", "scan", "screencap", "official art",
    # Sensitive subjects
    "child", "male child", "female child", "young", "loli", "shota",
    "aged down", "aged up",
    # Character-specific names (not in our LoRA library)
    "watson amelia", "hatsune miku",
    # Note: "midoriya izuku", "eureka" are valid LoRA triggers, not skipped
    # Copyright tags
    "vocaloid", "fate", "genshin impact", "blue archive",
    # Too vague or redundant
    "girl", "boy", "woman", "man", "female", "male",
    "anime", "manga", "illustration",  # Style is handled by 'style' category
])


def suggest_category_for_tag(tag: str) -> tuple[str, float]:
    """Suggest a category for a tag based on patterns.

    Returns:
        (category, confidence) where confidence is 0.0-1.0
    """
    normalized = tag.lower().replace("_", " ").strip()

    # Skip unwanted tags
    if normalized in SKIP_TAGS:
        return ("skip", 1.0)

    # Check each category's patterns
    best_category = ""
    best_score = 0.0

    tag_words = set(normalized.split())

    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            pattern_lower = pattern.lower()
            pattern_words = set(pattern_lower.split())

            # Exact match (100%)
            if normalized == pattern_lower:
                return (category, 1.0)

            # Tag contains pattern as complete word(s) (95%)
            # e.g., "white shirt" contains "shirt"
            if pattern_words.issubset(tag_words):
                score = 0.95
                if score > best_score:
                    best_score = score
                    best_category = category

            # Pattern contains tag as complete word(s) (90%)
            # e.g., "long sleeves" pattern matches "sleeves" tag
            elif tag_words.issubset(pattern_words) and len(normalized) >= 4:
                score = 0.9
                if score > best_score:
                    best_score = score
                    best_category = category

    return (best_category, best_score) if best_category else ("", 0.0)


def normalize_prompt_token(token: str) -> str:
    """Normalize a single prompt token for comparison/matching.

    CRITICAL: Preserves underscore format (Danbooru standard).
    - Danbooru tags use underscores: "brown_hair", "looking_at_viewer"
    - WD14 returns underscores: "brown_hair", "looking_at_viewer"
    - DB stores underscores: "brown_hair", "looking_at_viewer"
    - SD prompts use underscores: "brown_hair", "looking_at_viewer"

    All layers use the same format - no conversion needed.
    """
    cleaned = token.strip()
    if not cleaned:
        return ""
    if cleaned.startswith("<") and cleaned.endswith(">"):
        return ""
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = cleaned[1:-1]
    cleaned = re.sub(r":[0-9.]*$", "", cleaned)
    # Keep underscore format (Danbooru standard)
    return cleaned.strip().lower()


# --- DB-based keyword functions ---

# Mapping from DB group_name to Gemini-friendly category names
_DB_GROUP_TO_GEMINI_CATEGORY = {
    # Scene expression groups (세분화된 포즈/표정/시선/동작)
    "subject": "person/subject",
    "expression": "expression",
    "gaze": "gaze",
    "pose": "pose",
    "action": "action",
    "camera": "shot_type/camera_angle",
    # Environment (세분화)
    "environment": "location",  # Legacy - will be split
    "location_indoor": "indoor_location",
    "location_outdoor": "outdoor_location",
    "background_type": "background",
    "time_weather": "time/weather",
    "lighting": "lighting",
    # Others
    "mood": "mood",
    "style": "style",
    "quality": "quality",
    # Identity groups (for character, not for scene generation)
    "hair_color": None,  # Skip - character identity
    "hair_length": None,
    "hair_style": None,
    "hair_accessory": None,
    "eye_color": None,
    "skin_color": None,
    "body_feature": None,
    "appearance": None,
    "identity": None,
    "clothing": None,
}

# Groups to include in Gemini keyword context (scene-related only)
_SCENE_GROUPS = [
    "subject", "expression", "gaze", "pose", "action", "camera",
    "environment", "location_indoor", "location_outdoor", "background_type",
    "time_weather", "lighting", "mood", "style", "quality"
]


def load_tags_from_db() -> dict[str, list[str]]:
    """Load tags from database grouped by group_name."""
    from database import SessionLocal
    from models.tag import Tag

    db = SessionLocal()
    try:
        tags = db.query(Tag).order_by(Tag.group_name, Tag.name).all()
        grouped: dict[str, list[str]] = {}
        for tag in tags:
            group = tag.group_name or "other"
            if group not in grouped:
                grouped[group] = []
            grouped[group].append(tag.name)
        return grouped
    finally:
        db.close()


def load_synonyms_from_db() -> dict[str, str]:
    """Load synonym mappings from database. Returns {synonym: tag_name}."""
    from database import SessionLocal
    from models.tag import Synonym, Tag

    db = SessionLocal()
    try:
        synonyms = db.query(Synonym).join(Tag).all()
        return {
            normalize_prompt_token(s.synonym): normalize_prompt_token(s.tag.name)
            for s in synonyms if s.tag
        }
    finally:
        db.close()


def load_allowed_tags_from_db() -> set[str]:
    """Load all tag names from database as allowed set."""
    grouped = load_tags_from_db()
    allowed: set[str] = set()
    for tags in grouped.values():
        for tag in tags:
            allowed.add(normalize_prompt_token(tag))
    return allowed


def load_known_keywords() -> set[str]:
    """Load all known keywords from database."""
    allowed = load_allowed_tags_from_db()
    synonyms = load_synonyms_from_db()
    known = allowed.copy()
    known.update(synonyms.keys())
    known.update(IGNORE_TOKENS)
    return known


def expand_synonyms(tokens: list[str]) -> set[str]:
    """Expand a list of tokens to include all known synonyms (bidirectional)."""
    synonym_lookup = load_synonyms_from_db()  # {synonym: tag}
    # Reverse lookup: tag -> synonyms
    reverse_map: dict[str, set[str]] = {}
    for syn, tag in synonym_lookup.items():
        if tag not in reverse_map:
            reverse_map[tag] = set()
        reverse_map[tag].add(syn)

    expanded: set[str] = set()
    for token in tokens:
        if not token:
            continue
        normalized = normalize_prompt_token(token)
        expanded.add(normalized)
        # tag -> synonyms (e.g., "bust shot" -> {"upper body", "portrait"})
        if normalized in reverse_map:
            expanded.update(reverse_map[normalized])
        # synonym -> tag (e.g., "upper body" -> "bust shot")
        if normalized in synonym_lookup:
            expanded.add(synonym_lookup[normalized])
    return expanded


def load_tag_effectiveness_map() -> dict[str, tuple[float | None, int]]:
    """Load effectiveness scores for all tags. Returns {tag_name: (effectiveness, use_count)}."""
    from database import SessionLocal
    from models.tag import Tag, TagEffectiveness

    db = SessionLocal()
    try:
        results = (
            db.query(Tag.name, TagEffectiveness.effectiveness, TagEffectiveness.use_count)
            .outerjoin(TagEffectiveness, Tag.id == TagEffectiveness.tag_id)
            .all()
        )
        return {
            normalize_prompt_token(name): (eff, use_count or 0)
            for name, eff, use_count in results
        }
    finally:
        db.close()


def format_keyword_context(filter_by_effectiveness: bool = True) -> str:
    """Format keyword categories for use in Gemini prompts (DB-based).

    Args:
        filter_by_effectiveness: If True, filters out low-effectiveness tags
            and prioritizes high-effectiveness tags.
    """
    from config import (
        TAG_EFFECTIVENESS_THRESHOLD,
        TAG_MIN_USE_COUNT_FOR_FILTERING,
        RECOMMENDATION_EFFECTIVENESS_THRESHOLD,
        RECOMMENDATION_MIN_USE_COUNT,
    )

    grouped = load_tags_from_db()
    if not grouped:
        _get_logger().warning("No tags found in database")
        return ""

    # Load effectiveness data if filtering is enabled
    eff_map: dict[str, tuple[float | None, int]] = {}
    if filter_by_effectiveness:
        eff_map = load_tag_effectiveness_map()

    # Collect all tags with effectiveness data per category
    category_tags: dict[str, list[tuple[str, float, int]]] = {}
    recommended_tags: dict[str, list[str]] = {}

    for group in _SCENE_GROUPS:
        if group not in grouped:
            continue
        category_name = _DB_GROUP_TO_GEMINI_CATEGORY.get(group, group)
        if category_name is None:
            continue

        values = grouped[group]
        if not values:
            continue

        filtered_values = []
        category_recommended = []

        for tag in values:
            normalized = normalize_prompt_token(tag)
            eff_data = eff_map.get(normalized) if filter_by_effectiveness and eff_map else None

            if eff_data is None:
                # Unknown tag - include it (needs testing)
                filtered_values.append((tag, 0.5, 0))
            else:
                eff_score, use_count = eff_data
                if eff_score is None:
                    # No effectiveness data yet - include it
                    filtered_values.append((tag, 0.5, use_count))
                elif use_count < TAG_MIN_USE_COUNT_FOR_FILTERING:
                    # Not enough data - include it
                    filtered_values.append((tag, 0.5, use_count))
                elif eff_score < TAG_EFFECTIVENESS_THRESHOLD:
                    # Low effectiveness with sufficient data - skip
                    _get_logger().debug(f"Skipping low-effectiveness tag: {tag} ({eff_score:.2f})")
                    continue
                else:
                    filtered_values.append((tag, eff_score, use_count))

                    # Check if tag qualifies for recommendation
                    if (
                        eff_score is not None
                        and eff_score >= RECOMMENDATION_EFFECTIVENESS_THRESHOLD
                        and use_count >= RECOMMENDATION_MIN_USE_COUNT
                    ):
                        category_recommended.append(tag)

        # Sort by effectiveness (high first), then alphabetically
        filtered_values.sort(key=lambda x: (-x[1], x[0]))
        category_tags[category_name] = filtered_values

        if category_recommended:
            recommended_tags[category_name] = category_recommended

    # Build output with recommended section first
    lines = []

    # Add recommended tags section if any exist
    if recommended_tags:
        lines.append("Recommended High-Performance Tags (proven >80% effectiveness):")
        for category_name in _SCENE_GROUPS:
            gemini_category = _DB_GROUP_TO_GEMINI_CATEGORY.get(category_name, category_name)
            if gemini_category and gemini_category in recommended_tags:
                tags = recommended_tags[gemini_category]
                lines.append(f"- {gemini_category}: {', '.join(tags)}")
        lines.append("")  # blank line separator

    # Add all allowed keywords section
    lines.append("Allowed Keywords (use exactly as written):")
    for group in _SCENE_GROUPS:
        category_name = _DB_GROUP_TO_GEMINI_CATEGORY.get(group, group)
        if category_name and category_name in category_tags:
            values = [v[0] for v in category_tags[category_name]]
            if values:
                lines.append(f"- {category_name}: {', '.join(values)}")

    return "\n".join(lines)


def filter_prompt_tokens(prompt: str) -> str:
    """Filter prompt tokens to only include known/allowed keywords (DB-based).

    Enhanced with effectiveness-based filtering (Phase 6-4.21 Track 2):
    - Filters out low-effectiveness tags (< 30% with sufficient data)
    - Automatically replaces risky tags with safe alternatives
    - Logs warnings for problematic tags

    Handles both underscore and space formats for backward compatibility:
    - Normalized tags: "brown_hair", "full_body" (SD/Danbooru standard)
    - Legacy DB tags: "brown hair", "full body" (space format)
    """
    from config import TAG_EFFECTIVENESS_THRESHOLD, TAG_MIN_USE_COUNT_FOR_FILTERING
    from services.prompt import RISKY_TAG_REPLACEMENTS

    allowed = load_allowed_tags_from_db()
    synonym_lookup = load_synonyms_from_db()
    eff_map = load_tag_effectiveness_map()

    if not allowed:
        return _get_normalize_prompt_tokens()(prompt)

    tokens = _get_split_prompt_tokens()(prompt)
    cleaned: list[str] = []
    seen: set[str] = set()
    filtered_count = 0
    replaced_count = 0

    for token in tokens:
        normalized = normalize_prompt_token(token)
        if not normalized or normalized in IGNORE_TOKENS:
            continue

        # Check effectiveness first (before allowing)
        eff_data = eff_map.get(normalized)
        if eff_data:
            eff_score, use_count = eff_data
            # Filter low-effectiveness tags with sufficient data
            if (
                eff_score is not None
                and use_count >= TAG_MIN_USE_COUNT_FOR_FILTERING
                and eff_score < TAG_EFFECTIVENESS_THRESHOLD
            ):
                # Check for replacement
                space_format = normalized.replace("_", " ")
                replacement = RISKY_TAG_REPLACEMENTS.get(normalized) or RISKY_TAG_REPLACEMENTS.get(space_format)
                
                if replacement:
                    _get_logger().warning(
                        f"⚠️  [Filter] Replacing low-effectiveness tag: '{normalized}' "
                        f"(eff={eff_score:.1%}, n={use_count}) → '{replacement}'"
                    )
                    # Replace token with alternative (keep underscore format for SD)
                    token = replacement.replace(" ", "_")
                    normalized = normalize_prompt_token(replacement)
                    replaced_count += 1
                else:
                    _get_logger().warning(
                        f"❌ [Filter] Removing low-effectiveness tag: '{normalized}' "
                        f"(eff={eff_score:.1%}, n={use_count}, no replacement)"
                    )
                    filtered_count += 1
                    continue

        base = None
        output_token = None  # Token to output (preserves original format)

        # Try exact match first
        if normalized in allowed:
            base = normalized
            output_token = token  # Preserve original format (e.g., underscore)
        # Try synonym lookup
        elif normalized in synonym_lookup and synonym_lookup[normalized] in allowed:
            base = synonym_lookup[normalized]
            output_token = base  # Use canonical form for synonyms
        else:
            # Tag not in allowed list
            _get_logger().debug(f"⏭️  [Filter] Skipping unknown tag: '{normalized}'")
            continue

        if base and base not in seen:
            cleaned.append(output_token)
            seen.add(base)

    if filtered_count > 0 or replaced_count > 0:
        _get_logger().info(
            f"🔧 [Filter] Summary: {len(cleaned)} kept, {replaced_count} replaced, {filtered_count} removed"
        )

    return ", ".join(cleaned)


# --- Tag Rule Validation ---

def validate_prompt_tags(prompt_tags: list[str]) -> dict[str, Any]:
    """Validate prompt tags against conflict and requires rules.

    Args:
        prompt_tags: List of tag names in the prompt

    Returns:
        {
            "valid": bool,
            "conflicts": [{"tag1": str, "tag2": str, "message": str}, ...],
            "missing_dependencies": [{"tag": str, "requires": str, "message": str}, ...],
            "warnings": [str, ...]
        }
    """
    from database import SessionLocal
    from models.tag import Tag, TagRule

    if not prompt_tags:
        return {"valid": True, "conflicts": [], "missing_dependencies": [], "warnings": []}

    db = SessionLocal()
    try:
        # Normalize tags
        normalized_tags = {normalize_prompt_token(t) for t in prompt_tags if t}
        normalized_tags.discard("")

        # Get tag IDs for the prompt tags
        tag_lookup: dict[str, int] = {}
        tag_id_lookup: dict[int, str] = {}
        for name in normalized_tags:
            tag = db.query(Tag).filter(Tag.name == name).first()
            if not tag:
                tag = db.query(Tag).filter(Tag.name == name.replace(" ", "_")).first()
            if tag:
                tag_lookup[name] = tag.id
                tag_id_lookup[tag.id] = name

        tag_ids = set(tag_lookup.values())

        conflicts = []
        missing_deps = []
        warnings = []

        # Check conflict rules
        if tag_ids:
            conflict_rules = db.query(TagRule).filter(
                TagRule.rule_type == "conflict",
                TagRule.source_tag_id.in_(tag_ids),
                TagRule.target_tag_id.in_(tag_ids)
            ).all()

            seen_conflicts = set()
            for rule in conflict_rules:
                pair = tuple(sorted([rule.source_tag_id, rule.target_tag_id]))
                if pair not in seen_conflicts:
                    seen_conflicts.add(pair)
                    tag1 = tag_id_lookup.get(rule.source_tag_id, "?")
                    tag2 = tag_id_lookup.get(rule.target_tag_id, "?")
                    conflicts.append({
                        "tag1": tag1,
                        "tag2": tag2,
                        "message": f"'{tag1}' conflicts with '{tag2}'"
                    })

        # Check requires rules
        if tag_ids:
            requires_rules = db.query(TagRule).filter(
                TagRule.rule_type == "requires",
                TagRule.source_tag_id.in_(tag_ids)
            ).all()

            for rule in requires_rules:
                if rule.target_tag_id not in tag_ids:
                    source_name = tag_id_lookup.get(rule.source_tag_id, "?")
                    target_tag = db.query(Tag).filter(Tag.id == rule.target_tag_id).first()
                    target_name = target_tag.name if target_tag else "?"
                    missing_deps.append({
                        "tag": source_name,
                        "requires": target_name,
                        "message": f"'{source_name}' requires '{target_name}'"
                    })

        is_valid = len(conflicts) == 0 and len(missing_deps) == 0

        return {
            "valid": is_valid,
            "conflicts": conflicts,
            "missing_dependencies": missing_deps,
            "warnings": warnings
        }
    finally:
        db.close()


def sync_lora_triggers_to_tags() -> dict[str, Any]:
    """Sync LoRA trigger words to tags table.

    Reads all trigger words from loras table and ensures they exist
    in the tags table with appropriate categories.

    Returns:
        {"added": [...], "updated": [...], "skipped": [...]}
    """
    from database import SessionLocal
    from models.lora import LoRA
    from models.tag import Tag

    # Trigger word classification rules
    # Pattern-based classification for trigger words
    def classify_trigger(trigger: str, lora_type: str | None) -> tuple[str, str, int]:
        """Returns (group_name, category, priority)."""
        trigger_lower = trigger.lower()

        # Eye color patterns
        if "eyes" in trigger_lower:
            return ("eye_color", "character", 4)

        # Hair patterns
        if "hair" in trigger_lower:
            if any(c in trigger_lower for c in ["black", "blonde", "brown", "red", "blue", "green", "pink", "purple", "white", "silver", "grey", "gray", "orange", "aqua"]):
                return ("hair_color", "character", 4)
            elif any(length in trigger_lower for length in ["short", "long", "medium"]):
                return ("hair_length", "character", 4)
            else:
                return ("hair_style", "character", 4)

        # Style triggers
        if lora_type == "style" and trigger_lower in ["chibi", "blindbox", "figure", "anime", "realistic"]:
            return ("style", "scene", 16)

        # Expression triggers
        if trigger_lower in ["laughing", "crying", "smiling", "eyebrow", "eyebrow down", "eyebrow up"]:
            return ("expression", "scene", 6)

        # Default: treat as character identity (LoRA trigger)
        return ("identity", "character", 3)

    db = SessionLocal()
    try:
        added = []
        updated = []
        skipped = []

        loras = db.query(LoRA).all()

        for lora in loras:
            if not lora.trigger_words:
                continue

            for trigger in lora.trigger_words:
                if not trigger or not trigger.strip():
                    continue

                trigger_clean = trigger.strip().lower()
                group_name, category, priority = classify_trigger(trigger_clean, lora.lora_type)

                # Check if tag exists
                existing = db.query(Tag).filter(Tag.name == trigger_clean).first()

                if existing:
                    # Update if group is different and it's identity type
                    if existing.group_name != group_name and group_name == "identity":
                        existing.group_name = group_name
                        existing.priority = priority
                        updated.append({
                            "trigger": trigger_clean,
                            "lora": lora.name,
                            "group": group_name,
                        })
                    else:
                        skipped.append({
                            "trigger": trigger_clean,
                            "lora": lora.name,
                            "existing_group": existing.group_name,
                        })
                else:
                    # Add new tag
                    db.add(Tag(
                        name=trigger_clean,
                        category=category,
                        group_name=group_name,
                        priority=priority,
                        exclusive=False,
                    ))
                    added.append({
                        "trigger": trigger_clean,
                        "lora": lora.name,
                        "group": group_name,
                    })

        db.commit()

        return {
            "added": added,
            "updated": updated,
            "skipped": skipped,
            "summary": {
                "added_count": len(added),
                "updated_count": len(updated),
                "skipped_count": len(skipped),
            }
        }
    finally:
        db.close()


def sync_category_patterns_to_tags(update_existing: bool = False) -> dict[str, Any]:
    """Sync CATEGORY_PATTERNS to tags table.

    Reads all patterns from CATEGORY_PATTERNS and ensures they exist
    in the tags table with appropriate categories and priorities.

    Args:
        update_existing: If True, also update category/priority of existing tags.

    Returns:
        {"added": [...], "updated": [...], "skipped": [...], "summary": {...}}
    """
    from database import SessionLocal
    from models.tag import Tag

    # Map group_name to (db_category, priority)
    GROUP_TO_DB_CATEGORY: dict[str, tuple[str, int]] = {
        # Character-related
        "identity": ("character", 3),
        "hair_color": ("character", 4),
        "hair_length": ("character", 4),
        "hair_style": ("character", 4),
        "hair_accessory": ("character", 4),
        "eye_color": ("character", 4),
        "skin_color": ("character", 4),
        "body_feature": ("character", 4),
        "appearance": ("character", 4),
        "clothing": ("character", 5),
        # Quality (separate category for UI display)
        "quality": ("quality", 1),
        # Scene-related
        "subject": ("scene", 2),
        "expression": ("scene", 6),
        "gaze": ("scene", 7),
        "pose": ("scene", 8),
        "action": ("scene", 9),
        "camera": ("scene", 10),
        "location_indoor": ("scene", 11),
        "location_outdoor": ("scene", 11),
        "background_type": ("scene", 12),
        "time_weather": ("scene", 13),
        "lighting": ("scene", 14),
        "mood": ("scene", 15),
        "style": ("scene", 16),
    }

    db = SessionLocal()
    try:
        added = []
        updated = []
        skipped = []

        # Pre-fetch all existing tags for efficiency
        existing_tags = {t.name: t for t in db.query(Tag).all()}

        # Track tags we're adding in this batch to avoid duplicates
        batch_names: set[str] = set()

        for group_name, patterns in CATEGORY_PATTERNS.items():
            db_info = GROUP_TO_DB_CATEGORY.get(group_name)
            if not db_info:
                logger.warning("[Sync Patterns] Unknown group: %s", group_name)
                continue

            db_category, priority = db_info

            for pattern in patterns:
                tag_name = pattern.strip().lower()
                if not tag_name:
                    continue

                existing = existing_tags.get(tag_name)

                if existing:
                    # Update existing tag if update_existing is True
                    if update_existing:
                        changes = []
                        if existing.category != db_category:
                            changes.append(f"category: {existing.category}→{db_category}")
                            existing.category = db_category
                        if existing.group_name != group_name:
                            changes.append(f"group: {existing.group_name}→{group_name}")
                            existing.group_name = group_name
                        if existing.priority != priority:
                            changes.append(f"priority: {existing.priority}→{priority}")
                            existing.priority = priority

                        if changes:
                            updated.append({
                                "tag": tag_name,
                                "changes": changes,
                            })
                        else:
                            skipped.append({
                                "tag": tag_name,
                                "group": group_name,
                                "reason": "no changes needed",
                            })
                    else:
                        skipped.append({
                            "tag": tag_name,
                            "group": group_name,
                            "reason": "already in DB",
                        })
                elif tag_name in batch_names:
                    skipped.append({
                        "tag": tag_name,
                        "group": group_name,
                        "reason": "duplicate in patterns",
                    })
                else:
                    db.add(Tag(
                        name=tag_name,
                        category=db_category,
                        group_name=group_name,
                        priority=priority,
                        exclusive=False,
                    ))
                    batch_names.add(tag_name)
                    added.append({
                        "tag": tag_name,
                        "group": group_name,
                        "category": db_category,
                        "priority": priority,
                    })

        db.commit()
        logger.info(
            "[Sync Patterns Complete] added=%d updated=%d skipped=%d",
            len(added), len(updated), len(skipped)
        )

        return {
            "added": added,
            "updated": updated,
            "skipped": skipped,
            "summary": {
                "added_count": len(added),
                "updated_count": len(updated),
                "skipped_count": len(skipped),
                "by_group": _count_by_group(added),
            }
        }
    finally:
        db.close()


def _count_by_group(items: list[dict]) -> dict[str, int]:
    """Count items by group_name."""
    counts: dict[str, int] = {}
    for item in items:
        group = item.get("group", "unknown")
        counts[group] = counts.get(group, 0) + 1
    return counts


def get_tag_rules_summary() -> dict[str, Any]:
    """Get summary of all tag rules in the database."""
    from database import SessionLocal
    from models.tag import Tag, TagRule

    db = SessionLocal()
    try:
        conflict_count = db.query(TagRule).filter(TagRule.rule_type == "conflict").count()
        requires_count = db.query(TagRule).filter(TagRule.rule_type == "requires").count()

        # Get some examples
        conflict_examples = []
        requires_examples = []

        conflict_rules = db.query(TagRule).filter(TagRule.rule_type == "conflict").limit(10).all()
        for rule in conflict_rules:
            source = db.query(Tag).filter(Tag.id == rule.source_tag_id).first()
            target = db.query(Tag).filter(Tag.id == rule.target_tag_id).first()
            if source and target:
                conflict_examples.append(f"{source.name} ↔ {target.name}")

        requires_rules = db.query(TagRule).filter(TagRule.rule_type == "requires").limit(10).all()
        for rule in requires_rules:
            source = db.query(Tag).filter(Tag.id == rule.source_tag_id).first()
            target = db.query(Tag).filter(Tag.id == rule.target_tag_id).first()
            if source and target:
                requires_examples.append(f"{source.name} → {target.name}")

        return {
            "conflict_count": conflict_count // 2,  # Divide by 2 because conflicts are bidirectional
            "requires_count": requires_count,
            "conflict_examples": conflict_examples[:5],
            "requires_examples": requires_examples[:5],
        }
    finally:
        db.close()


# --- Keyword suggestions (still file-based for simplicity) ---

def update_keyword_suggestions(unknown_tags: list[str]) -> None:
    """Update the keyword suggestions cache with newly encountered unknown tags.

    Tags are normalized to underscore format (Danbooru standard) before storage.
    """
    if not unknown_tags:
        return
    suggestions_path = _get_cache_dir() / "keyword_suggestions.json"
    try:
        if suggestions_path.exists():
            data = json.loads(suggestions_path.read_text(encoding="utf-8"))
        else:
            data = {}
        for tag in unknown_tags:
            # Normalize tag to underscore format (Danbooru standard)
            # Space → underscore, then apply normalize_prompt_token
            normalized_tag = normalize_prompt_token(tag.replace(" ", "_"))
            if not normalized_tag:
                continue
            data[normalized_tag] = int(data.get(normalized_tag, 0)) + 1
        suggestions_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception:
        _get_logger().exception("Failed to update keyword suggestions")


def load_keyword_suggestions(min_count: int = 1, limit: int = 50) -> list[dict[str, Any]]:
    """Load keyword suggestions filtered by minimum count with category suggestions.

    Returns normalized tags (underscore format, Danbooru standard).
    """
    suggestions_path = _get_cache_dir() / "keyword_suggestions.json"
    if not suggestions_path.exists():
        return []
    try:
        data = json.loads(suggestions_path.read_text(encoding="utf-8"))
    except Exception:
        _get_logger().exception("Failed to read keyword suggestions")
        return []
    known = load_known_keywords()
    items = []
    for tag, count in data.items():
        # Normalize tag to underscore format (Danbooru standard)
        # Space → underscore, then apply normalize_prompt_token (defensive)
        normalized_tag = normalize_prompt_token(tag.replace(" ", "_"))
        if not normalized_tag:
            continue
        if int(count) >= min_count and normalized_tag not in known:
            category, confidence = suggest_category_for_tag(normalized_tag)
            items.append({
                "tag": normalized_tag,
                "count": int(count),
                "suggested_category": category,
                "confidence": confidence,
            })
    items.sort(key=lambda item: (-item["count"], item["tag"]))
    return items[:max(1, limit)]


# --- Tag Effectiveness Feedback Loop ---

def update_tag_effectiveness(
    prompt_tags: list[str],
    detected_tags: list[dict[str, Any]],
) -> dict[str, Any]:
    """Update tag effectiveness based on WD14 detection results.

    Args:
        prompt_tags: Tags used in the prompt (e.g., ["smile", "sitting", "library"])
        detected_tags: WD14 detection results (e.g., [{"tag": "smile", "confidence": 0.95}, ...])

    Returns:
        Summary of updates: {"updated": [...], "new": [...], "stats": {...}}
    """
    from database import SessionLocal
    from models.tag import Tag, TagEffectiveness

    if not prompt_tags:
        return {"updated": [], "new": [], "stats": {}}

    # Normalize prompt tags
    normalized_prompt = {normalize_prompt_token(t) for t in prompt_tags if t}
    normalized_prompt.discard("")

    # Build detected tag lookup: {normalized_name: confidence}
    detected_lookup: dict[str, float] = {}
    for item in detected_tags:
        tag_name = item.get("tag", "")
        confidence = float(item.get("confidence", 0.0))
        normalized = normalize_prompt_token(tag_name)
        if normalized:
            # Keep highest confidence if duplicate
            if normalized not in detected_lookup or confidence > detected_lookup[normalized]:
                detected_lookup[normalized] = confidence

    db = SessionLocal()
    try:
        updated = []
        new_records = []

        for tag_name in normalized_prompt:
            # Find tag in DB (normalized format = space format)
            tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                continue

            # Get or create effectiveness record
            eff = db.query(TagEffectiveness).filter(TagEffectiveness.tag_id == tag.id).first()
            if not eff:
                eff = TagEffectiveness(tag_id=tag.id, use_count=0, match_count=0, total_confidence=0.0)
                db.add(eff)
                new_records.append(tag_name)

            # Update counts
            eff.use_count += 1

            # Check if this tag was detected
            if tag_name in detected_lookup:
                eff.match_count += 1
                eff.total_confidence += detected_lookup[tag_name]

            # Recalculate effectiveness
            if eff.use_count > 0:
                eff.effectiveness = eff.match_count / eff.use_count

            updated.append({
                "tag": tag_name,
                "use_count": eff.use_count,
                "match_count": eff.match_count,
                "effectiveness": round(eff.effectiveness, 3),
                "detected": tag_name in detected_lookup,
            })

        db.commit()

        return {
            "updated": updated,
            "new": new_records,
            "stats": {
                "prompt_tags": len(normalized_prompt),
                "detected_tags": len(detected_lookup),
                "records_updated": len(updated),
            },
        }
    except Exception as e:
        db.rollback()
        _get_logger().exception("Failed to update tag effectiveness")
        return {"error": str(e), "updated": [], "new": [], "stats": {}}
    finally:
        db.close()


def get_effective_tags(min_effectiveness: float = 0.5, min_uses: int = 5) -> dict[str, list[str]]:
    """Get tags grouped by effectiveness level.

    Args:
        min_effectiveness: Minimum effectiveness score to be considered "effective"
        min_uses: Minimum use count to be considered reliable data

    Returns:
        {"high": [...], "medium": [...], "low": [...], "unknown": [...]}
    """
    from database import SessionLocal
    from models.tag import Tag, TagEffectiveness

    db = SessionLocal()
    try:
        # Get all tags with effectiveness data
        results = (
            db.query(Tag.name, Tag.group_name, TagEffectiveness.effectiveness, TagEffectiveness.use_count)
            .outerjoin(TagEffectiveness, Tag.id == TagEffectiveness.tag_id)
            .filter(Tag.group_name.in_([
                "expression", "gaze", "pose", "action", "camera",
                "environment", "location_indoor", "location_outdoor",
                "background_type", "time_weather", "lighting", "mood"
            ]))
            .all()
        )

        high = []  # effectiveness >= 0.7
        medium = []  # 0.4 <= effectiveness < 0.7
        low = []  # effectiveness < 0.4
        unknown = []  # no data or insufficient uses

        for name, _group, effectiveness, use_count in results:
            if effectiveness is None or (use_count or 0) < min_uses:
                unknown.append(name)
            elif effectiveness >= 0.7:
                high.append(name)
            elif effectiveness >= 0.4:
                medium.append(name)
            else:
                low.append(name)

        return {"high": high, "medium": medium, "low": low, "unknown": unknown}
    finally:
        db.close()


def get_tag_effectiveness_report() -> list[dict[str, Any]]:
    """Get full effectiveness report for all scene-related tags."""
    from database import SessionLocal
    from models.tag import Tag, TagEffectiveness

    db = SessionLocal()
    try:
        results = (
            db.query(
                Tag.name,
                Tag.group_name,
                TagEffectiveness.use_count,
                TagEffectiveness.match_count,
                TagEffectiveness.effectiveness,
            )
            .outerjoin(TagEffectiveness, Tag.id == TagEffectiveness.tag_id)
            .filter(Tag.group_name.in_([
                "expression", "gaze", "pose", "action", "camera",
                "environment", "location_indoor", "location_outdoor",
                "background_type", "time_weather", "lighting", "mood", "style"
            ]))
            .order_by(TagEffectiveness.effectiveness.desc().nullslast(), Tag.name)
            .all()
        )

        return [
            {
                "tag": name,
                "group": group,
                "use_count": use_count or 0,
                "match_count": match_count or 0,
                "effectiveness": round(effectiveness, 3) if effectiveness else None,
            }
            for name, group, use_count, match_count, effectiveness in results
        ]
    finally:
        db.close()
