"""Pure V3 Prompt Composition Service with 12-Layer System.

NOTE: This module uses inline `.lower().replace(" ", "_").strip()` for tag
normalization. This is equivalent to `normalize_prompt_token()` from
`services.keywords.core` but kept inline to avoid circular imports and
minimize risk in the composition hot-path. Do NOT refactor to external calls
without validating all tag paths.
"""

import functools

from sqlalchemy.orm import Session

from config import (
    BACKGROUND_SCENE_MARKER,
    BISHOUNEN_WEIGHT,
    CAMERA_FRAMING_CLOSE,
    CAMERA_FRAMING_MID,
    CAMERA_FRAMING_WIDE,
    CHARACTER_CAMERA_TAGS,
    ENVIRONMENT_WEIGHT_BOOST,
    EXCLUSIVE_TAG_GROUPS,
    EXPRESSION_ACTION_WEIGHT_BOOST,
    FALLBACK_STYLE_LORA_WEIGHT_MAX,
    FEMALE_INDICATORS,
    GENERIC_LOCATION_TAGS,
    INDOOR_LOCATION_TAGS,
    MALE_FOCUS_WEIGHT,
    MALE_GENDER_BOOST_WEIGHT,
    MALE_INDICATORS,
    NON_FRONTAL_GAZE_TAGS,
    NON_FRONTAL_GAZE_WEIGHT,
    OUTDOOR_LOCATION_TAGS,
    PERMANENT_DETAIL_WEIGHT_BOOST,
    PERMANENT_IDENTITY_WEIGHT_BOOST,
    REFERENCE_CAMERA_TAGS,
    REFERENCE_ENV_TAGS,
    STYLE_LORA_WEIGHT_CAP,
)
from database import SessionLocal
from models.character import Character
from models.lora import LoRA
from models.tag import Tag
from services.keywords.db_cache import LoRATriggerCache, TagAliasCache, TagFilterCache, TagRuleCache

# Defined Layers (from PROMPT_LAYERS.md)
LAYER_QUALITY = 0
LAYER_SUBJECT = 1
LAYER_IDENTITY = 2  # Character LoRA & Triggers
LAYER_BODY = 3
LAYER_MAIN_CLOTH = 4
LAYER_DETAIL_CLOTH = 5
LAYER_ACCESSORY = 6
LAYER_EXPRESSION = 7
LAYER_ACTION = 8
LAYER_CAMERA = 9
LAYER_ENVIRONMENT = 10
LAYER_ATMOSPHERE = 11  # Style LoRA & Artistic Style

LAYER_NAMES: list[str] = [
    "Quality",
    "Subject",
    "Identity",
    "Body",
    "Main Cloth",
    "Detail Cloth",
    "Accessory",
    "Expression",
    "Action",
    "Camera",
    "Environment",
    "Atmosphere",
]

# Layers that only apply when a character is present (SUBJECT through ACTION)
CHARACTER_ONLY_LAYERS = frozenset(range(LAYER_SUBJECT, LAYER_ACTION + 1))


class LoRAInfo:
    """LoRA 메타데이터 (weight, lora_type, trigger_words)."""

    __slots__ = ("weight", "lora_type", "trigger_words")

    def __init__(self, weight: float, lora_type: str | None, trigger_words: list[str]):
        self.weight = weight
        self.lora_type = lora_type
        self.trigger_words = trigger_words


class V3PromptBuilder:
    """Prompt builder using the 12-layer semantic staking system."""

    def __init__(self, db: Session, sd_model_base: str | None = None):
        self.db = db
        self.sd_model_base = sd_model_base
        self.warnings: list[str] = []
        self._lora_info_cache: dict[str, LoRAInfo] = {}
        self._db_tag_names: set[str] | None = None
        self._last_composed_layers: list[list[str]] | None = None

    @staticmethod
    def _strip_weight(token: str) -> str:
        """Strip SD weight syntax: (tag:1.2) → tag, bare tag → tag."""
        if token.startswith("(") and ":" in token and token.endswith(")"):
            return token[1:].split(":")[0]
        return token

    def get_tag_info(self, tag_names: list[str]) -> dict[str, dict]:
        """Fetches metadata for a list of tags from the DB with pattern-based fallback.

        Handles SD weight syntax transparently: (crying:1.1) is looked up as 'crying'
        but keyed by the original normalized form so callers can match either way.
        """
        if not tag_names:
            return {}

        # Normalize and strip weight syntax for DB lookup
        normalized_names = [t.lower().replace(" ", "_").strip() for t in tag_names]
        bare_names = [self._strip_weight(n) for n in normalized_names]

        unique_bare = list(set(bare_names))
        tags = self.db.query(Tag).filter(Tag.name.in_(unique_bare)).all()

        # Cache DB-found tag names (bare form) for find_unknown_tags reuse
        self._db_tag_names = {tag.name for tag in tags}

        bare_result: dict[str, dict] = {
            tag.name: {
                "layer": tag.default_layer,
                "scope": tag.usage_scope,
                "group_name": tag.group_name,
            }
            for tag in tags
        }

        # Pattern-based fallback for DB-missing tags (bare form)
        group_map = self._tag_to_group_map()
        for bare in unique_bare:
            if bare not in bare_result:
                layer = self._infer_layer_from_pattern(bare)
                bare_result[bare] = {"layer": layer, "scope": "ANY", "group_name": group_map.get(bare)}

        # Map results back: key by normalized (may include weight) AND bare form
        result: dict[str, dict] = {}
        for norm, bare in zip(normalized_names, bare_names):
            if bare in bare_result:
                result[norm] = bare_result[bare]
                if norm != bare:
                    result[bare] = bare_result[bare]

        return result

    def find_unknown_tags(self, tag_names: list[str]) -> list[str]:
        """Return tags not found in DB or CATEGORY_PATTERNS (potential non-Danbooru tags).

        Skips LoRA tags (<lora:...>), weighted tokens ((tag:1.2)),
        and tags registered in CATEGORY_PATTERNS (known valid SD tokens).
        """
        if not tag_names:
            return []

        normalized = []
        for t in tag_names:
            stripped = t.strip()
            if stripped.startswith("<lora:"):
                continue
            stripped = self._strip_weight(stripped)
            stripped = stripped.lower().replace(" ", "_").strip()
            if stripped:
                normalized.append(stripped)

        if not normalized:
            return []

        # Known valid tags: DB cache + CATEGORY_PATTERNS
        known = self._known_pattern_tags()
        if self._db_tag_names is not None:
            known = known | self._db_tag_names
            return [t for t in normalized if t not in known]

        found = {tag.name for tag in self.db.query(Tag.name).filter(Tag.name.in_(normalized)).all()}
        known = known | found
        return [t for t in normalized if t not in known]

    @staticmethod
    @functools.cache
    def _known_pattern_tags() -> frozenset[str]:
        """CATEGORY_PATTERNS의 모든 태그를 flat set으로 반환 (캐시)."""
        from services.keywords.patterns import CATEGORY_PATTERNS

        return frozenset(tag for tags in CATEGORY_PATTERNS.values() for tag in tags)

    @staticmethod
    @functools.cache
    def _pattern_tags_by_category() -> dict[str, frozenset[str]]:
        """CATEGORY_PATTERNS를 category별 frozenset으로 반환 (캐시)."""
        from services.keywords.patterns import CATEGORY_PATTERNS

        return {k: frozenset(v) for k, v in CATEGORY_PATTERNS.items()}

    @staticmethod
    @functools.cache
    def _tag_to_layer_map() -> dict[str, int]:
        """CATEGORY_PATTERNS 전체를 tag→layer flat dict로 변환 (캐시).

        GROUP_NAME_TO_LAYER를 SSOT로 사용하여 26개 카테고리 700+태그를
        O(1) lookup 가능한 dict로 만든다.
        """
        from services.keywords.patterns import CATEGORY_PATTERNS, GROUP_NAME_TO_LAYER

        result: dict[str, int] = {}
        for group_name, tags in CATEGORY_PATTERNS.items():
            layer = GROUP_NAME_TO_LAYER.get(group_name)
            if layer is None:
                continue
            for tag in tags:
                if tag not in result:
                    result[tag] = layer
        return result

    @staticmethod
    @functools.cache
    def _tag_to_group_map() -> dict[str, str]:
        """CATEGORY_PATTERNS 전체를 tag→group_name flat dict로 변환 (캐시).

        _tag_to_layer_map()과 동일 패턴으로 group_name을 O(1) lookup.
        """
        from services.keywords.patterns import CATEGORY_PATTERNS

        result: dict[str, str] = {}
        for group_name, tags in CATEGORY_PATTERNS.items():
            for tag in tags:
                if tag not in result:
                    result[tag] = group_name
        return result

    @staticmethod
    def _infer_layer_from_pattern(tag: str) -> int:
        """Infer layer from tag pattern when not found in DB.

        3-tier resolution:
        1. Exact lookup in _tag_to_layer_map() (26 categories, 700+ tags, O(1))
        2. Suffix/prefix heuristics for novel tags
        3. LAYER_SUBJECT fallback
        """
        # ── 1순위: CATEGORY_PATTERNS exact match ──
        tag_map = V3PromptBuilder._tag_to_layer_map()
        if tag in tag_map:
            return tag_map[tag]

        # ── 2순위: suffix/prefix 휴리스틱 (novel 태그용) ──
        # Hair
        if tag.endswith("_hair") or "hair" in tag:
            return LAYER_IDENTITY
        # Eyes
        if tag.endswith("_eyes") or "eyes" in tag:
            return LAYER_IDENTITY
        # Clothing suffixes
        if tag.endswith(("_dress", "_shirt", "_skirt", "_pants", "_uniform", "_outfit", "_suit", "_coat", "_jacket")):
            return LAYER_MAIN_CLOTH
        # Accessory suffixes
        if tag.endswith(("_earrings", "_necklace", "_bracelet", "_ribbon", "_bow", "_hairpin", "_headband")):
            return LAYER_ACCESSORY
        # Lighting suffixes
        if tag.endswith("_lighting") or tag.endswith("_light"):
            return LAYER_ATMOSPHERE
        # Action patterns (verb-ing, exclude "earring" etc.)
        if tag.endswith("ing") and not tag.endswith("ring"):
            return LAYER_ACTION
        # Camera patterns
        if tag.endswith("_shot") or tag.endswith("_view") or tag.startswith("from_"):
            return LAYER_CAMERA
        # Background patterns
        if tag.endswith("_background") or tag.endswith("_room"):
            return LAYER_ENVIRONMENT

        # ── 3순위: fallback ──
        return LAYER_SUBJECT

    # ── Background scene handling ────────────────────────────────────────

    @staticmethod
    def _is_background_scene(tags: list[str]) -> bool:
        """Detect background-only scene by presence of no_humans tag."""
        return any(t.lower().replace(" ", "_").strip() == BACKGROUND_SCENE_MARKER for t in tags)

    @staticmethod
    def _cap_lora_weight(weight: float) -> float:
        """Apply STYLE_LORA_WEIGHT_CAP to prevent LoRA overfitting."""
        return round(min(weight, STYLE_LORA_WEIGHT_CAP), 2)

    def _compose_background_scene(
        self,
        scene_tags: list[str],
        style_loras: list[dict] | None = None,
    ) -> str:
        """Compose prompt for background-only scenes (no_humans).

        Skips CHARACTER_ONLY_LAYERS and character-specific camera tags.
        Keeps QUALITY, ENVIRONMENT, ATMOSPHERE, and background-safe CAMERA.
        """
        scene_tags = self._resolve_aliases(scene_tags)
        layers: list[list[str]] = [[] for _ in range(12)]
        tag_info = self.get_tag_info(scene_tags)

        for tag in scene_tags:
            norm_tag = tag.lower().replace(" ", "_").strip()
            info = tag_info.get(norm_tag, {"layer": LAYER_SUBJECT})
            target_layer = info["layer"]

            # Skip character-only layers
            if target_layer in CHARACTER_ONLY_LAYERS:
                continue
            # Skip character-specific camera framing
            if target_layer == LAYER_CAMERA and norm_tag in CHARACTER_CAMERA_TAGS:
                continue

            layers[target_layer].append(tag)

        # Ensure no_humans is present in ENVIRONMENT
        env_norms = {t.lower().replace(" ", "_").strip() for t in layers[LAYER_ENVIRONMENT]}
        if BACKGROUND_SCENE_MARKER not in env_norms:
            layers[LAYER_ENVIRONMENT].insert(0, BACKGROUND_SCENE_MARKER)

        # Style LoRAs — LoRA tag only; trigger words omitted for background
        # scenes to prevent semantic bias toward character generation.
        if style_loras:
            for lora in style_loras:
                weight = lora.get("weight")
                if weight is None:
                    weight = self.get_lora_weight_by_name(lora["name"])
                layers[LAYER_ATMOSPHERE].append(f"<lora:{lora['name']}:{self._cap_lora_weight(weight)}>")

        layers[LAYER_ENVIRONMENT] = self._resolve_location_conflicts(layers[LAYER_ENVIRONMENT])
        layers[LAYER_CAMERA] = self._resolve_camera_conflicts(layers[LAYER_CAMERA])
        self._ensure_quality_tags(layers)

        return self._flatten_layers(layers)

    # ── compose_for_background (Phase 18 Stage) ─────────────────────────

    def compose_for_background(
        self,
        location_tags: list[str],
        quality_tags: list[str] | None = None,
        style_loras: list[dict] | None = None,
    ) -> str:
        """Build a 5-Layer background prompt for Stage Workflow.

        Layers used: Quality(0), Subject(1), Camera(9), Environment(10), Atmosphere(11).
        Character layers (2-8) are fully skipped.

        Args:
            location_tags: Environment tags from WriterPlan location (e.g. ["classroom", "indoors", "desk"]).
            quality_tags: StyleProfile quality tags. Falls back to FALLBACK_QUALITY_TAGS.
            style_loras: Style LoRAs from StyleContext (trigger words omitted for background).
        """
        location_tags = self._resolve_aliases(location_tags)
        layers: list[list[str]] = [[] for _ in range(12)]

        # L0 Quality
        if quality_tags:
            layers[LAYER_QUALITY].extend(quality_tags)

        # L1 Subject — no_humans + scenery + style-aware enforcement
        layers[LAYER_SUBJECT].extend([BACKGROUND_SCENE_MARKER, "scenery"])
        if self._is_anime_style(quality_tags):
            layers[LAYER_SUBJECT].extend([
                "(anime_coloring:1.5)", "(flat_color:1.0)", "(illustration:1.3)",
                "(2d:1.2)", "(colorful:1.2)", "anime_style",
            ])

        # L9 Camera — wide_shot default for background
        layers[LAYER_CAMERA].append("wide_shot")

        # L10 Environment — location tags
        tag_info = self.get_tag_info(location_tags)
        for tag in location_tags:
            norm = tag.lower().replace(" ", "_").strip()
            info = tag_info.get(norm, {"layer": LAYER_ENVIRONMENT})
            target = info["layer"]
            if target in CHARACTER_ONLY_LAYERS:
                continue
            if target == LAYER_CAMERA and norm in CHARACTER_CAMERA_TAGS:
                continue
            layers[target].append(tag)

        # L11 Atmosphere — Style LoRA (trigger words omitted)
        if style_loras:
            for lora in style_loras:
                weight = lora.get("weight")
                if weight is None:
                    weight = self.get_lora_weight_by_name(lora["name"])
                layers[LAYER_ATMOSPHERE].append(f"<lora:{lora['name']}:{self._cap_lora_weight(weight)}>")

        layers[LAYER_ENVIRONMENT] = self._resolve_location_conflicts(layers[LAYER_ENVIRONMENT])
        layers[LAYER_CAMERA] = self._resolve_camera_conflicts(layers[LAYER_CAMERA])
        self._ensure_quality_tags(layers)

        return self._flatten_layers(layers)

    @staticmethod
    def _is_anime_style(quality_tags: list[str] | None) -> bool:
        """Detect anime style from quality tags (derived from StyleProfile.default_positive)."""
        if not quality_tags:
            return True  # default to anime when no style info
        joined = " ".join(t.lower().replace("_", " ") for t in quality_tags)
        return any(kw in joined for kw in ("anime", "cel shading", "illustration", "2d"))

    @staticmethod
    def _strip_character_layers(layers: list[list[str]]) -> None:
        """Clear character-only layers and character camera tags (defense for generic compose)."""
        for i in CHARACTER_ONLY_LAYERS:
            layers[i].clear()
        layers[LAYER_CAMERA] = [
            t for t in layers[LAYER_CAMERA] if t.lower().replace(" ", "_").strip() not in CHARACTER_CAMERA_TAGS
        ]

    @classmethod
    def _strip_char_base_from_scene(cls, character: "Character", scene_tags: list[str]) -> list[str]:
        """Remove character base prompt tokens from scene_tags to prevent duplication.

        When frontend sends a pre-composed prompt, it already contains character
        base tokens (from custom_base_prompt). Stripping them ensures compose
        doesn't double-include them and allows scene override to work.
        """
        if not character.custom_base_prompt:
            return scene_tags
        base_tokens = {
            cls._strip_weight(bt.strip().lower().replace(" ", "_"))
            for bt in character.custom_base_prompt.split(",")
            if bt.strip()
        }
        if not base_tokens:
            return scene_tags
        return [t for t in scene_tags if cls._strip_weight(t.strip().lower().replace(" ", "_")) not in base_tokens]

    # ── compose_for_character ────────────────────────────────────────────

    def compose_for_character(
        self,
        character_id: int,
        scene_tags: list[str],
        style_loras: list[dict] | None = None,
        character: Character | None = None,
        scene_character_actions: list[dict] | None = None,
        clothing_override: list[str] | None = None,
    ) -> str:
        """Composes a prompt specifically for a Character project."""
        # Defense: character_id is explicitly set, so strip no_humans instead of
        # routing to background scene (Gemini may incorrectly include it)
        if self._is_background_scene(scene_tags):
            from config import logger as _logger

            scene_tags = [t for t in scene_tags if t.lower().replace(" ", "_").strip() != BACKGROUND_SCENE_MARKER]
            _logger.warning(
                "⚠️ [V3 Builder] Stripped no_humans from compose_for_character (character_id=%d)",
                character_id,
            )

        if character is None:
            character = self.db.query(Character).filter(Character.id == character_id).first()
        if not character:
            return self.compose(scene_tags, style_loras=style_loras)

        # 1-2. Collect character tags (DB + custom_base_prompt)
        char_tags_data = self._collect_character_tags(character)

        # 2b. Strip character base tokens from scene_tags to prevent duplication
        # (Frontend may send pre-composed prompt that already includes char base tokens)
        scene_tags = self._strip_char_base_from_scene(character, scene_tags)

        # 3. Resolve aliases and get scene tag info
        scene_tags = self._resolve_aliases(scene_tags)
        scene_tag_info = self.get_tag_info(scene_tags)

        # 4. Initialize 12 layers
        layers: list[list[str]] = [[] for _ in range(12)]

        # 5-6. Distribute character + scene tags into layers
        self._distribute_tags(char_tags_data, scene_tags, scene_tag_info, layers)

        # 6b. Override clothing layers if scene-specific clothing is provided
        if clothing_override:
            self._apply_clothing_override(clothing_override, layers)

        # 6c. Override with scene-specific character actions
        if scene_character_actions:
            self._apply_scene_character_actions(character.id, scene_character_actions, layers)

        # 7-9. Inject LoRAs (character, scene-triggered, style)
        self._inject_loras(character, scene_tags, layers, style_loras)

        # 10. Gender enhancement for male characters (SD model bias)
        self._apply_gender_enhancement(character, char_tags_data, layers)

        # 11. Resolve environment and camera conflicts
        layers[LAYER_ENVIRONMENT] = self._resolve_location_conflicts(layers[LAYER_ENVIRONMENT])
        layers[LAYER_CAMERA] = self._resolve_camera_conflicts(layers[LAYER_CAMERA])

        # 12. Ensure quality tags
        self._ensure_quality_tags(layers)

        return self._flatten_layers(layers)

    def _collect_character_tags(self, character: Character) -> list[dict]:
        """Collect character tags from DB associations + custom_base_prompt.

        DB tags: layer/group_name from Tag model.
        custom_base_prompt tags: layer/group_name resolved via get_tag_info()
        (DB lookup → pattern fallback) instead of hardcoding LAYER_IDENTITY.
        """
        char_tags_data = []
        for char_tag in character.tags:
            tag = char_tag.tag
            char_tags_data.append(
                {
                    "name": tag.name,
                    "layer": tag.default_layer,
                    "weight": char_tag.weight,
                    "is_permanent": char_tag.is_permanent,
                    "group_name": tag.group_name,
                }
            )

        TagFilterCache.initialize(self.db)
        if character.custom_base_prompt:
            custom_tags = [t.strip() for t in character.custom_base_prompt.split(",")]
            custom_tags = [bt for bt in custom_tags if bt and not TagFilterCache.is_restricted(bt)]

            if custom_tags:
                normalized = [bt.lower().replace(" ", "_").strip() for bt in custom_tags]
                tag_info_map = self.get_tag_info(normalized)

                for bt, norm in zip(custom_tags, normalized):
                    info = tag_info_map.get(norm, {})
                    char_tags_data.append(
                        {
                            "name": bt,
                            "layer": info.get("layer", LAYER_IDENTITY),
                            "weight": 1.0,
                            "is_permanent": True,
                            "group_name": info.get("group_name"),
                        }
                    )

        return char_tags_data

    def _build_char_occupied_groups(self, char_tags_data: list[dict]) -> set[str]:
        """Identify exclusive semantic groups occupied by character tags."""
        names = [ct["name"].lower().replace(" ", "_").strip() for ct in char_tags_data]
        if not names:
            return set()

        info_map = self.get_tag_info(names)
        return {info["group_name"] for info in info_map.values() if info.get("group_name") in EXCLUSIVE_TAG_GROUPS}

    def _distribute_tags(
        self,
        char_tags_data: list[dict],
        scene_tags: list[str],
        scene_tag_info: dict[str, dict],
        layers: list[list[str]],
    ) -> set[str]:
        """Distribute character and scene tags into layers.

        Character tags are placed first. Scene tags in exclusive groups
        already occupied by the character are dropped.
        Scene override: when a scene provides tags in a group NOT in
        EXCLUSIVE_TAG_GROUPS, matching character base tags are suppressed.
        Returns the set of occupied exclusive groups.
        """
        # 5a. Collect scene groups dynamically (exclude identity groups)
        scene_override_groups: set[str] = set()
        for tag in scene_tags:
            norm = tag.lower().replace(" ", "_").strip()
            info = scene_tag_info.get(norm, {})
            gn = info.get("group_name")
            if gn and gn not in EXCLUSIVE_TAG_GROUPS:
                scene_override_groups.add(gn)

        # 5b. Distribute character tags (with identity/clothing weight boost)
        for ct in char_tags_data:
            # Skip character base tags whose group is overridden by scene
            if ct.get("group_name") in scene_override_groups:
                continue
            token = ct["name"]
            weight = ct["weight"]
            # Boost permanent identity/clothing tags (skip custom-weighted tags)
            if ct.get("is_permanent", False) and weight == 1.0:
                if ct["layer"] in (LAYER_IDENTITY, LAYER_BODY, LAYER_MAIN_CLOTH):
                    weight = PERMANENT_IDENTITY_WEIGHT_BOOST
                elif ct["layer"] in (LAYER_DETAIL_CLOTH, LAYER_ACCESSORY):
                    weight = PERMANENT_DETAIL_WEIGHT_BOOST
            if weight != 1.0:
                token = f"({token}:{weight})"
            layers[ct["layer"]].append(token)

        # 5c. Build character-occupied exclusive groups
        char_occupied = self._build_char_occupied_groups(char_tags_data)

        # 6. Distribute scene tags (skip occupied exclusive groups + LoRA tags)
        for tag in scene_tags:
            if tag.strip().startswith("<lora:"):
                continue  # LoRA injection handled by _inject_loras
            norm_tag = tag.lower().replace(" ", "_").strip()
            info = scene_tag_info.get(norm_tag, {"layer": LAYER_SUBJECT, "group_name": None})
            if info.get("group_name") in char_occupied:
                continue  # Character tag takes priority
            layers[info["layer"]].append(tag)

        return char_occupied

    def _apply_clothing_override(self, clothing_tags: list[str], layers: list[list[str]]) -> None:
        """Replace default clothing layers with scene-specific override tags.

        Clears LAYER_MAIN_CLOTH, LAYER_DETAIL_CLOTH, LAYER_ACCESSORY,
        then distributes each override tag to its correct layer via tag_info
        lookup (DB → pattern fallback). Tags that resolve outside the three
        clothing layers default to LAYER_MAIN_CLOTH.
        """
        CLOTHING_LAYERS = (LAYER_MAIN_CLOTH, LAYER_DETAIL_CLOTH, LAYER_ACCESSORY)
        for idx in CLOTHING_LAYERS:
            layers[idx].clear()

        # Resolve each tag to its proper clothing layer
        tag_info = self.get_tag_info(clothing_tags)
        for tag in clothing_tags:
            norm = tag.lower().replace(" ", "_").strip()
            info = tag_info.get(norm, {})
            target_layer = info.get("layer", LAYER_MAIN_CLOTH)
            # Constrain to clothing layers only; out-of-range defaults to MAIN_CLOTH
            if target_layer not in CLOTHING_LAYERS:
                target_layer = LAYER_MAIN_CLOTH
            layers[target_layer].append(tag)

    def _apply_scene_character_actions(
        self,
        character_id: int,
        actions: list[dict],
        layers: list[list[str]],
    ) -> None:
        """Override expression/action layers with scene-specific character actions.

        Filters actions for the given character_id, resolves tag metadata,
        and replaces existing tokens in LAYER_EXPRESSION/LAYER_ACTION when
        the new tag targets those layers (scene actions override character defaults).
        """
        # Filter actions for this character
        my_actions = [a for a in actions if a.get("character_id") == character_id]
        if not my_actions:
            return

        # Batch resolve tag_ids to Tag objects
        tag_ids = [a["tag_id"] for a in my_actions]
        tags = self.db.query(Tag).filter(Tag.id.in_(tag_ids)).all()
        tag_map = {t.id: t for t in tags}

        # Track which layers get overrides (clear existing for override layers)
        override_layers: set[int] = set()
        pending: list[tuple[int, str]] = []  # (layer, token)

        for action in my_actions:
            tag = tag_map.get(action["tag_id"])
            if not tag:
                continue
            target_layer = tag.default_layer
            weight = action.get("weight", 1.0)
            token = f"({tag.name}:{weight})" if weight != 1.0 else tag.name

            # Mark expression/action layers for override
            if target_layer in (LAYER_EXPRESSION, LAYER_ACTION):
                override_layers.add(target_layer)

            pending.append((target_layer, token))

        # Clear overridden layers (scene actions replace character defaults)
        for layer_idx in override_layers:
            layers[layer_idx].clear()

        # Insert new tokens
        for target_layer, token in pending:
            layers[target_layer].append(token)

    def _inject_loras(
        self,
        character: Character,
        scene_tags: list[str],
        layers: list[list[str]],
        style_loras: list[dict] | None,
    ) -> None:
        """Inject character LoRAs, scene-triggered LoRAs, and style LoRAs."""
        active_loras: dict[str, LoRAInfo] = {}

        # Character LoRAs (style-type skipped; StyleProfile is SSOT for style)
        if character.loras and character.prompt_mode != "standard":
            for lora_info in character.loras:
                lora_id = lora_info.get("lora_id")
                weight = lora_info.get("weight")
                lora_obj = self.db.query(LoRA).filter(LoRA.id == lora_id).first()
                if lora_obj:
                    if lora_obj.lora_type == "style":
                        continue  # StyleProfile handles style LoRAs uniformly
                    # Check base_model compatibility
                    if self.sd_model_base and lora_obj.base_model and lora_obj.base_model != self.sd_model_base:
                        msg = (
                            f"LoRA '{lora_obj.name}' (base: {lora_obj.base_model}) "
                            f"may be incompatible with checkpoint (base: {self.sd_model_base})"
                        )
                        self.warnings.append(msg)
                        from config import logger as _logger

                        _logger.warning("LoRA compatibility: %s", msg)
                    if weight is None:
                        weight = self.get_effective_lora_weight(lora_obj)
                    active_loras[lora_obj.name] = LoRAInfo(weight, lora_obj.lora_type, lora_obj.trigger_words or [])
                    for trigger in lora_obj.trigger_words or []:
                        if not self._trigger_exists_in_layers(trigger, layers):
                            layers[LAYER_IDENTITY].append(trigger)

        # Scene-triggered LoRAs (+ 트리거 워드 주입)
        for tag in scene_tags:
            lora_name = LoRATriggerCache.get_lora_name(tag)
            if lora_name and lora_name not in active_loras:
                info = self._get_lora_info(lora_name)
                active_loras[lora_name] = info
                target = LAYER_ATMOSPHERE if info.lora_type == "style" else LAYER_IDENTITY
                for trigger in info.trigger_words:
                    if not self._trigger_exists_in_layers(trigger, layers):
                        layers[target].append(trigger)

        # Inject LoRA tags into layers
        for name, info in active_loras.items():
            target_layer = LAYER_ATMOSPHERE if info.lora_type == "style" else LAYER_IDENTITY
            layers[target_layer].append(f"<lora:{name}:{self._cap_lora_weight(info.weight)}>")

        # Style LoRAs (explicit overrides or character fallback)
        effective_style_loras = style_loras
        if not effective_style_loras and character.loras and character.prompt_mode != "standard":
            # Fallback: use character's style LoRAs when no StyleProfile
            effective_style_loras = self._extract_character_style_loras(character)

        if effective_style_loras:
            is_fallback = not style_loras
            for lora_info in effective_style_loras:
                name: str = lora_info.get("name", "")
                if name in active_loras:
                    continue  # Already injected via scene-triggered detection
                weight = lora_info.get("weight")
                if weight is None:
                    weight = self.get_lora_weight_by_name(name)
                # Fallback style LoRAs: cap to avoid interference with character LoRA
                if is_fallback:
                    weight = min(weight, FALLBACK_STYLE_LORA_WEIGHT_MAX)
                for trigger in lora_info.get("trigger_words", []):
                    if not self._trigger_exists_in_layers(trigger, layers):
                        layers[LAYER_ATMOSPHERE].append(trigger)
                layers[LAYER_ATMOSPHERE].append(f"<lora:{name}:{self._cap_lora_weight(weight)}>")

    def _extract_character_style_loras(self, character: Character) -> list[dict]:
        """Extract style LoRAs from character's loras JSONB for fallback use."""
        result = []
        for lora_info in character.loras or []:
            lora_id = lora_info.get("lora_id")
            lora_obj = self.db.query(LoRA).filter(LoRA.id == lora_id).first()
            if lora_obj and lora_obj.lora_type == "style":
                result.append(
                    {
                        "name": lora_obj.name,
                        "weight": lora_info.get("weight") or self.get_effective_lora_weight(lora_obj),
                        "trigger_words": lora_obj.trigger_words or [],
                    }
                )
        return result

    @staticmethod
    def _ensure_quality_tags(layers: list[list[str]]) -> None:
        """Ensure quality tags exist; skip if StyleProfile already provided them.

        If LAYER_QUALITY is non-empty (e.g. realistic quality tags from StyleProfile),
        respect those as-is. Only inject FALLBACK_QUALITY_TAGS when the layer is empty.
        """
        if layers[LAYER_QUALITY]:
            return

        from config import FALLBACK_QUALITY_TAGS

        for tag in FALLBACK_QUALITY_TAGS:
            layers[LAYER_QUALITY].append(tag)

    # ── compose (generic, no character) ──────────────────────────────────

    def compose(
        self,
        tags: list[str],
        character_loras: list[dict] | None = None,
        style_loras: list[dict] | None = None,
    ) -> str:
        """Generic composition without direct DB character object."""
        tags = self._resolve_aliases(tags)
        layers: list[list[str]] = [[] for _ in range(12)]
        tag_info = self.get_tag_info(tags)

        for tag in tags:
            norm_tag = tag.lower().replace(" ", "_").strip()
            info = tag_info.get(norm_tag, {"layer": LAYER_SUBJECT})
            layers[info["layer"]].append(tag)

        # LoRA dedup: track injected names across all sources
        style_lora_names = {lora["name"] for lora in (style_loras or [])}
        injected_lora_names: set[str] = set()

        if character_loras:
            for lora in character_loras:
                lora_name = lora["name"]
                # StyleProfile LoRAs take precedence over character LoRAs
                if lora_name in style_lora_names:
                    continue

                for trigger in lora.get("trigger_words", []):
                    if not self._trigger_exists_in_layers(trigger, layers):
                        layers[LAYER_IDENTITY].append(trigger)

                weight = lora.get("weight")
                if weight is None:
                    weight = self.get_lora_weight_by_name(lora_name)
                layers[LAYER_IDENTITY].append(f"<lora:{lora_name}:{self._cap_lora_weight(weight)}>")
                injected_lora_names.add(lora_name)

        # Auto-triggered LoRAs from tags (+ 트리거 워드 주입)
        for tag in tags:
            lora_name = LoRATriggerCache.get_lora_name(tag)
            if lora_name:
                if lora_name in style_lora_names or lora_name in injected_lora_names:
                    continue
                info = self._get_lora_info(lora_name)
                target = LAYER_ATMOSPHERE if info.lora_type == "style" else LAYER_IDENTITY
                layers[target].append(f"<lora:{lora_name}:{self._cap_lora_weight(info.weight)}>")
                for trigger in info.trigger_words:
                    if not self._trigger_exists_in_layers(trigger, layers):
                        layers[target].append(trigger)
                injected_lora_names.add(lora_name)

        _style_trigger_words: set[str] = set()
        if style_loras:
            for lora in style_loras:
                lora_name = lora["name"]
                if lora_name in injected_lora_names:
                    continue
                for trigger in lora.get("trigger_words", []):
                    if not self._trigger_exists_in_layers(trigger, layers):
                        layers[LAYER_ATMOSPHERE].append(trigger)
                    _style_trigger_words.add(trigger)

                weight = lora.get("weight")
                if weight is None:
                    weight = self.get_lora_weight_by_name(lora_name)
                layers[LAYER_ATMOSPHERE].append(f"<lora:{lora_name}:{self._cap_lora_weight(weight)}>")
                injected_lora_names.add(lora_name)

        # Background scene defense: strip character layers + style trigger words
        if self._is_background_scene(tags):
            self._strip_character_layers(layers)
            if _style_trigger_words:
                layers[LAYER_ATMOSPHERE] = [t for t in layers[LAYER_ATMOSPHERE] if t not in _style_trigger_words]

        layers[LAYER_ENVIRONMENT] = self._resolve_location_conflicts(layers[LAYER_ENVIRONMENT])
        layers[LAYER_CAMERA] = self._resolve_camera_conflicts(layers[LAYER_CAMERA])
        self._ensure_quality_tags(layers)

        return self._flatten_layers(layers)

    # ── Shared utilities ─────────────────────────────────────────────────

    def _resolve_aliases(self, tags: list[str]) -> list[str]:
        """Replace aliased tags using TagAliasCache.

        Returns filtered list: aliases resolved, None-mapped tags dropped.
        """
        TagAliasCache.initialize(self.db)
        resolved: list[str] = []
        for tag in tags:
            replacement = TagAliasCache.get_replacement(tag)
            if replacement is ...:
                resolved.append(tag)  # No alias — keep original
            elif replacement is None:
                continue  # Tag mapped to nothing — drop it
            else:
                resolved.append(replacement)
        return resolved

    def _apply_gender_enhancement(
        self, character: "Character", char_tags_data: list[dict], layers: list[list[str]]
    ) -> None:
        """Add male enhancement tags if character is male (SD model bias fix)."""
        gender = (character.gender or "").lower()
        if not gender:
            all_names = {ct["name"].lower().strip("()").split(":")[0] for ct in char_tags_data}
            for token in list(all_names) + [t.lower() for t in (layers[LAYER_SUBJECT] + layers[LAYER_IDENTITY])]:
                if token in MALE_INDICATORS:
                    gender = "male"
                    break
                if token in FEMALE_INDICATORS:
                    gender = "female"
                    break

        if gender == "male":
            male_tags = [
                f"(1boy:{MALE_GENDER_BOOST_WEIGHT})",
                f"(male_focus:{MALE_FOCUS_WEIGHT})",
                f"(bishounen:{BISHOUNEN_WEIGHT})",
            ]
            # Remove conflicting female subject tags before adding male enhancement
            layers[LAYER_SUBJECT] = [t for t in layers[LAYER_SUBJECT] if self._dedup_key(t) not in FEMALE_INDICATORS]
            for tag in male_tags:
                if tag not in layers[LAYER_SUBJECT]:
                    layers[LAYER_SUBJECT].append(tag)

    @staticmethod
    def _dedup_key(token: str) -> str:
        """Normalize token for dedup: strip weights and unify format.

        - (1boy:1.3) → 1boy
        - <lora:flat_color:0.76> → <lora:flat_color> (ignore weight)
        - "flat color" → "flat_color" (space→underscore, Danbooru 표준 정규화)
        """
        t = token.strip().lower()
        if t.startswith("<lora:") and t.endswith(">"):
            name = t[6:-1].split(":")[0]
            return f"<lora:{name}>"
        if t.startswith("(") and ":" in t and t.endswith(")"):
            t = t[1:].split(":")[0]
        # LoRA trigger word("flat color")와 tag("flat_color") 동일시
        t = t.replace(" ", "_")
        return t

    @staticmethod
    def _trigger_exists_in_layers(trigger: str, layers: list[list[str]]) -> bool:
        """Check if a LoRA trigger word already exists in any layer (normalized).

        Uses _dedup_key for consistency with _flatten_layers dedup logic,
        so weighted tags like (flat_color:1.15) are also matched.
        """
        norm = V3PromptBuilder._dedup_key(trigger)
        for layer_tokens in layers:
            for t in layer_tokens:
                if V3PromptBuilder._dedup_key(t) == norm:
                    return True
        return False

    def _flatten_layers(self, layers: list[list[str]]) -> str:
        """Flattens 12 layers into a final string with global deduplication and conflict resolution."""
        TagRuleCache.initialize(self.db)

        final_tokens = []
        global_seen: set[str] = set()
        composed: list[list[str]] = [[] for _ in range(12)]

        for i, layer_tokens in enumerate(layers):
            if layer_tokens:
                unique_layer_tokens = []
                for t in layer_tokens:
                    key = self._dedup_key(t)
                    if key not in global_seen:
                        has_conflict = False
                        for existing_key in global_seen:
                            if TagRuleCache.is_conflicting(key, existing_key):
                                has_conflict = True
                                break

                        if not has_conflict:
                            unique_layer_tokens.append(t)
                            global_seen.add(key)

                unique_layer_tokens = self._apply_layer_boosts(i, unique_layer_tokens)
                composed[i] = unique_layer_tokens
                final_tokens.extend(unique_layer_tokens)

        self._last_composed_layers = composed
        return ", ".join(final_tokens)

    @staticmethod
    def _apply_layer_boosts(layer_idx: int, tokens: list[str]) -> list[str]:
        """레이어별 가중치 부스트 적용. 이미 가중치가 있는 태그는 건너뛴다."""
        if layer_idx in (LAYER_EXPRESSION, LAYER_ACTION):
            return [
                f"({t}:{NON_FRONTAL_GAZE_WEIGHT if t in NON_FRONTAL_GAZE_TAGS else EXPRESSION_ACTION_WEIGHT_BOOST})"
                if ":" not in t
                else t
                for t in tokens
            ]
        if layer_idx == LAYER_ENVIRONMENT:
            return [
                f"({t}:{ENVIRONMENT_WEIGHT_BOOST})"
                if ":" not in t and t.lower().replace(" ", "_").strip() not in GENERIC_LOCATION_TAGS
                else t
                for t in tokens
            ]
        return tokens

    def get_last_composed_layers(self) -> list[dict] | None:
        """Return layer breakdown from the last compose/flatten call."""
        if self._last_composed_layers is None:
            return None
        return [
            {"index": i, "name": LAYER_NAMES[i], "tokens": tokens}
            for i, tokens in enumerate(self._last_composed_layers)
            if tokens
        ]

    def get_effective_lora_weight(self, lora: LoRA) -> float:
        """Helper to get calibrated weight from LoRA object."""
        if lora.optimal_weight is not None:
            return float(lora.optimal_weight)
        if lora.default_weight is not None:
            return float(lora.default_weight)
        return 0.7

    def _get_lora_info(self, name: str) -> LoRAInfo:
        """Looks up LoRA weight, type, and trigger_words by name with caching."""
        if name in self._lora_info_cache:
            return self._lora_info_cache[name]

        lora = self.db.query(LoRA).filter(LoRA.name == name).first()
        if not lora:
            info = LoRAInfo(0.7, None, [])
        else:
            info = LoRAInfo(
                self.get_effective_lora_weight(lora),
                lora.lora_type,
                lora.trigger_words or [],
            )

        self._lora_info_cache[name] = info
        return info

    def get_lora_weight_by_name(self, name: str) -> float:
        """Looks up LoRA weight by name with caching."""
        return self._get_lora_info(name).weight

    # ── Conflict resolution ──────────────────────────────────────────────

    def _resolve_location_conflicts(self, env_tokens: list[str]) -> list[str]:
        """Remove conflicting location tags (indoor vs outdoor) from the environment layer.

        When both indoor and outdoor tags coexist, keep only the majority side.
        Within the winning side, keep ALL specific tags (cafe, classroom, etc.)
        plus generic tags (indoors/outdoors). Non-location tags (props) pass through.
        """
        if not env_tokens:
            return env_tokens

        outdoor_found = []
        indoor_found = []
        neutral = []

        for token in env_tokens:
            norm = self._dedup_key(token)
            if norm in OUTDOOR_LOCATION_TAGS:
                outdoor_found.append(token)
            elif norm in INDOOR_LOCATION_TAGS:
                indoor_found.append(token)
            else:
                neutral.append(token)

        if outdoor_found and indoor_found:
            winner = outdoor_found if len(outdoor_found) >= len(indoor_found) else indoor_found
        else:
            winner = outdoor_found + indoor_found

        specific = []
        generic_tags = []
        for token in winner:
            norm = self._dedup_key(token)
            if norm in GENERIC_LOCATION_TAGS:
                generic_tags.append(token)
            else:
                specific.append(token)

        return specific + generic_tags + neutral

    def _resolve_camera_conflicts(self, cam_tokens: list[str]) -> list[str]:
        """Keep only one framing tag when conflicts exist."""
        if not cam_tokens:
            return cam_tokens

        all_camera = CAMERA_FRAMING_WIDE | CAMERA_FRAMING_MID | CAMERA_FRAMING_CLOSE
        first_framing = None
        result = []

        for token in cam_tokens:
            norm = token.lower().replace(" ", "_").strip()
            if norm in all_camera:
                if first_framing is None:
                    first_framing = token
                    result.append(token)
            else:
                result.append(token)

        return result

    # ── compose_for_reference ────────────────────────────────────────────

    def compose_for_reference(
        self,
        character: Character,
        reference_extra_tags: list[str] | None = None,
        quality_tags: list[str] | None = None,
    ) -> str:
        """Compose prompt for character reference image generation.

        Differences from compose_for_character:
        - Character LoRA: weight × REFERENCE_LORA_SCALE (identity hint only)
        - Style LoRA: full weight (not skipped)
        - Environment: white_background fixed
        - No scene_tags (Gemini)
        - quality_tags: explicit quality tags from StyleProfile (skips anime fallback)
        """
        # 1. Collect character tags (DB + custom_base_prompt)
        char_tags_data = self._collect_character_tags(character)

        # 2. Parse reference_base_prompt for extra correction tags
        ref_tags = self._parse_reference_tags(character.reference_base_prompt)
        if reference_extra_tags:
            ref_tags.extend(reference_extra_tags)

        # 3. Resolve aliases on all tag names & build lookup set
        all_tag_names = [ct["name"] for ct in char_tags_data] + ref_tags
        resolved_names = self._resolve_aliases(all_tag_names)
        resolved_set = {n.lower().replace(" ", "_").strip() for n in resolved_names}

        # 3-1. Build original→resolved mapping for char_tags_data
        orig_char_names = [ct["name"] for ct in char_tags_data]
        resolved_char_names = resolved_names[: len(orig_char_names)]
        for ct, resolved in zip(char_tags_data, resolved_char_names, strict=True):
            ct["name"] = resolved  # alias 해소 결과 반영

        # 4. Get tag info for reference tags
        ref_tag_info = self.get_tag_info(ref_tags) if ref_tags else {}

        # 5. Initialize 12 layers; pre-fill quality if provided by StyleProfile
        layers: list[list[str]] = [[] for _ in range(12)]
        if quality_tags:
            layers[LAYER_QUALITY].extend(quality_tags)

        for ct in char_tags_data:
            name = ct["name"]
            # Skip if already resolved away by alias
            if name.lower().replace(" ", "_").strip() not in resolved_set:
                continue
            token = name
            if ct["weight"] != 1.0:
                token = f"({name}:{ct['weight']})"
            layers[ct["layer"]].append(token)

        # 6. Distribute reference tags into layers by tag_info
        for tag in ref_tags:
            norm = tag.lower().replace(" ", "_").strip()
            info = ref_tag_info.get(norm, {"layer": self._infer_layer_from_pattern(norm)})
            layer_idx = info if isinstance(info, int) else info.get("layer", LAYER_SUBJECT)
            layers[layer_idx].append(tag)

        # 7. Quality tags (before reference defaults — env tags fill LAYER_QUALITY too)
        self._ensure_quality_tags(layers)

        # 8. Inject reference defaults (white_background, camera)
        self._inject_reference_defaults(layers)

        # 9. Inject LoRAs (character × scale, style full weight)
        self._inject_loras_for_reference(character, layers)

        # 10. Gender enhancement
        self._apply_gender_enhancement(character, char_tags_data, layers)

        # 11. Flatten with dedup + conflict resolution
        return self._flatten_layers(layers)

    def _parse_reference_tags(self, prompt: str | None) -> list[str]:
        """Parse reference_base_prompt into individual tags, filtering restricted ones."""
        if not prompt:
            return []
        TagFilterCache.initialize(self.db)
        tags = []
        for token in prompt.split(","):
            t = token.strip()
            if t and not TagFilterCache.is_restricted(t):
                tags.append(t)
        return tags

    def _inject_reference_defaults(self, layers: list[list[str]]) -> None:
        """Inject fixed environment and camera tags for reference images.

        Background tags are placed in LAYER_QUALITY (front of prompt) for maximum
        influence — SD pays more attention to earlier tokens.
        """
        # Background suppression → LAYER_QUALITY (position 0) for maximum priority
        quality_norms = {self._strip_weight(t).lower().replace(" ", "_") for t in layers[LAYER_QUALITY]}
        for tag in REFERENCE_ENV_TAGS:
            key = self._strip_weight(tag).lower().replace(" ", "_")
            if key not in quality_norms:
                layers[LAYER_QUALITY].append(tag)
                quality_norms.add(key)

        cam_norms = {self._strip_weight(t).lower().replace(" ", "_") for t in layers[LAYER_CAMERA]}
        for tag in REFERENCE_CAMERA_TAGS:
            key = self._strip_weight(tag).lower().replace(" ", "_")
            if key not in cam_norms:
                layers[LAYER_CAMERA].append(tag)
                cam_norms.add(key)

    def _inject_loras_for_reference(
        self,
        character: Character,
        layers: list[list[str]],
    ) -> None:
        """Inject LoRAs for reference: character LoRA × REFERENCE_LORA_SCALE, style LoRA × REFERENCE_STYLE_LORA_SCALE.

        Uses batch query to avoid N+1.
        """
        from config import REFERENCE_LORA_SCALE, REFERENCE_STYLE_LORA_SCALE

        if not character.loras:
            return

        # Batch query all LoRA objects (N+1 prevention)
        lora_ids = [entry.get("lora_id") for entry in character.loras if entry.get("lora_id")]
        if not lora_ids:
            return
        lora_objs = self.db.query(LoRA).filter(LoRA.id.in_(lora_ids)).all()
        lora_map = {lora.id: lora for lora in lora_objs}

        for lora_entry in character.loras:
            lora_id = lora_entry.get("lora_id")
            if not lora_id:
                continue
            lora_obj = lora_map.get(lora_id)
            if not lora_obj:
                continue

            base_weight = lora_entry.get("weight")
            if base_weight is None:
                base_weight = self.get_effective_lora_weight(lora_obj)

            if lora_obj.lora_type == "style":
                # Style LoRA: scaled down to prevent character sheet composition
                weight = round(base_weight * REFERENCE_STYLE_LORA_SCALE, 2)
                weight = self._cap_lora_weight(weight)
                layers[LAYER_ATMOSPHERE].append(f"<lora:{lora_obj.name}:{weight}>")
            else:
                # Character LoRA: scaled down for identity hint
                weight = round(base_weight * REFERENCE_LORA_SCALE, 2)
                weight = self._cap_lora_weight(weight)
                layers[LAYER_IDENTITY].append(f"<lora:{lora_obj.name}:{weight}>")
                # Add trigger words for character LoRAs only
                for trigger in lora_obj.trigger_words or []:
                    if not self._trigger_exists_in_layers(trigger, layers):
                        layers[LAYER_IDENTITY].append(trigger)


def get_v3_prompt_builder():
    db = SessionLocal()
    try:
        yield V3PromptBuilder(db)
    finally:
        db.close()
