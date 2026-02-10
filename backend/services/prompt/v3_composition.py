"""Pure V3 Prompt Composition Service with 12-Layer System.

NOTE: This module uses inline `.lower().replace(" ", "_").strip()` for tag
normalization. This is equivalent to `normalize_prompt_token()` from
`services.keywords.core` but kept inline to avoid circular imports and
minimize risk in the composition hot-path. Do NOT refactor to external calls
without validating all tag paths.
"""

from sqlalchemy.orm import Session

from config import STYLE_LORA_WEIGHT_CAP
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

# Layers that only apply when a character is present (SUBJECT through ACTION)
CHARACTER_ONLY_LAYERS = frozenset(range(LAYER_SUBJECT, LAYER_ACTION + 1))

# Character-specific camera framing tags — filtered from LAYER_CAMERA for background scenes
_CHARACTER_CAMERA_TAGS = frozenset(
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

# Exclusive semantic groups: character tags take priority over scene tags.
# When a character occupies a group (e.g. hair_color=red_hair),
# scene tags in the same group (e.g. brown_hair) are dropped.
EXCLUSIVE_GROUPS = frozenset(
    {
        "hair_color",
        "eye_color",
        "hair_length",
        "skin_color",
    }
)


class V3PromptBuilder:
    """Prompt builder using the 12-layer semantic staking system."""

    def __init__(self, db: Session):
        self.db = db
        self._lora_info_cache: dict[str, tuple[float, str | None]] = {}

    def get_tag_info(self, tag_names: list[str]) -> dict[str, dict]:
        """Fetches metadata for a list of tags from the DB with pattern-based fallback."""
        if not tag_names:
            return {}

        # Normalize tags for DB lookup
        normalized_names = [t.lower().replace(" ", "_").strip() for t in tag_names]

        tags = self.db.query(Tag).filter(Tag.name.in_(normalized_names)).all()
        result = {
            tag.name: {
                "layer": tag.default_layer,
                "scope": tag.usage_scope,
                "group_name": tag.group_name,
            }
            for tag in tags
        }

        # Pattern-based fallback for DB-missing tags
        for normalized in normalized_names:
            if normalized not in result:
                layer = self._infer_layer_from_pattern(normalized)
                result[normalized] = {"layer": layer, "scope": "ANY", "group_name": None}

        return result

    def find_unknown_tags(self, tag_names: list[str]) -> list[str]:
        """Return tags not found in DB (potential non-Danbooru tags).

        Skips LoRA tags (<lora:...>), weighted tokens ((tag:1.2)),
        and common quality tags that may not be in DB.
        """
        if not tag_names:
            return []

        normalized = []
        for t in tag_names:
            stripped = t.strip()
            if stripped.startswith("<lora:"):
                continue
            # Strip weight parens: (tag:1.2) → tag
            if stripped.startswith("(") and ":" in stripped and stripped.endswith(")"):
                stripped = stripped[1:].split(":")[0]
            stripped = stripped.lower().replace(" ", "_").strip()
            if stripped:
                normalized.append(stripped)

        if not normalized:
            return []

        found = {
            tag.name
            for tag in self.db.query(Tag.name).filter(Tag.name.in_(normalized)).all()
        }
        return [t for t in normalized if t not in found]

    @staticmethod
    def _infer_layer_from_pattern(tag: str) -> int:
        """Infer layer from tag pattern when not found in DB.

        Pattern matching rules:
        - *_hair, *_colored_hair → LAYER_IDENTITY (hair color)
        - *_eyes, *_colored_eyes → LAYER_IDENTITY (eye color)
        - Known expressions → LAYER_EXPRESSION (checked before *ing)
        - *ing (e.g., running, walking) → LAYER_ACTION
        - *_shot, *_view, from_* → LAYER_CAMERA
        - Default: LAYER_SUBJECT
        """
        # Expression patterns (check BEFORE *ing to prioritize)
        expression_keywords = {
            "smiling",
            "crying",
            "angry",
            "sad",
            "happy",
            "surprised",
            "confused",
            "blushing",
            "embarrassed",
            "scared",
            "worried",
            "nervous",
        }
        if tag in expression_keywords:
            return LAYER_EXPRESSION

        # Hair patterns
        if tag.endswith("_hair") or "hair" in tag:
            return LAYER_IDENTITY

        # Eye patterns
        if tag.endswith("_eyes") or "eyes" in tag:
            return LAYER_IDENTITY

        # Action patterns (verb-ing)
        if tag.endswith("ing") and not tag.endswith("ring"):  # Exclude "earring", etc.
            return LAYER_ACTION

        # Camera patterns
        if tag.endswith("_shot") or tag.endswith("_view") or tag.startswith("from_"):
            return LAYER_CAMERA

        # Default fallback
        return LAYER_SUBJECT

    # ── Background scene handling ────────────────────────────────────────

    @staticmethod
    def _is_background_scene(tags: list[str]) -> bool:
        """Detect background-only scene by presence of no_humans tag."""
        return any(t.lower().replace(" ", "_").strip() == "no_humans" for t in tags)

    @staticmethod
    def _cap_lora_weight(weight: float) -> float:
        """Apply STYLE_LORA_WEIGHT_CAP to prevent LoRA overfitting."""
        return min(weight, STYLE_LORA_WEIGHT_CAP)

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
            if target_layer == LAYER_CAMERA and norm_tag in _CHARACTER_CAMERA_TAGS:
                continue

            layers[target_layer].append(tag)

        # Ensure no_humans is present in ENVIRONMENT
        env_norms = {t.lower().replace(" ", "_").strip() for t in layers[LAYER_ENVIRONMENT]}
        if "no_humans" not in env_norms:
            layers[LAYER_ENVIRONMENT].insert(0, "no_humans")

        # Style LoRAs (visual consistency)
        if style_loras:
            for lora in style_loras:
                for trigger in lora.get("trigger_words", []):
                    if trigger not in layers[LAYER_ATMOSPHERE]:
                        layers[LAYER_ATMOSPHERE].append(trigger)
                weight = lora.get("weight")
                if weight is None:
                    weight = self.get_lora_weight_by_name(lora["name"])
                layers[LAYER_ATMOSPHERE].append(f"<lora:{lora['name']}:{self._cap_lora_weight(weight)}>")

        layers[LAYER_ENVIRONMENT] = self._resolve_location_conflicts(layers[LAYER_ENVIRONMENT])
        layers[LAYER_CAMERA] = self._resolve_camera_conflicts(layers[LAYER_CAMERA])
        self._ensure_quality_tags(layers)

        return self._flatten_layers(layers)

    @staticmethod
    def _strip_character_layers(layers: list[list[str]]) -> None:
        """Clear character-only layers and character camera tags (defense for generic compose)."""
        for i in CHARACTER_ONLY_LAYERS:
            layers[i].clear()
        layers[LAYER_CAMERA] = [
            t for t in layers[LAYER_CAMERA] if t.lower().replace(" ", "_").strip() not in _CHARACTER_CAMERA_TAGS
        ]

    # ── compose_for_character ────────────────────────────────────────────

    def compose_for_character(
        self,
        character_id: int,
        scene_tags: list[str],
        style_loras: list[dict] | None = None,
    ) -> str:
        """Composes a prompt specifically for a Character project."""
        # Background scene: skip character DB lookup entirely
        if self._is_background_scene(scene_tags):
            return self._compose_background_scene(scene_tags, style_loras)

        character = self.db.query(Character).filter(Character.id == character_id).first()
        if not character:
            return self.compose(scene_tags, style_loras=style_loras)

        # 1-2. Collect character tags (DB + custom_base_prompt)
        char_tags_data = self._collect_character_tags(character)

        # 3. Resolve aliases and get scene tag info
        scene_tags = self._resolve_aliases(scene_tags)
        scene_tag_info = self.get_tag_info(scene_tags)

        # 4. Initialize 12 layers
        layers: list[list[str]] = [[] for _ in range(12)]

        # 5-6. Distribute character + scene tags into layers
        self._distribute_tags(char_tags_data, scene_tags, scene_tag_info, layers)

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
        """Collect character tags from DB associations + custom_base_prompt."""
        char_tags_data = []
        for char_tag in character.tags:
            tag = char_tag.tag
            char_tags_data.append(
                {
                    "name": tag.name,
                    "layer": tag.default_layer,
                    "weight": char_tag.weight,
                }
            )

        TagFilterCache.initialize(self.db)
        if character.custom_base_prompt:
            for bt in (t.strip() for t in character.custom_base_prompt.split(",")):
                if bt and not TagFilterCache.is_restricted(bt):
                    char_tags_data.append(
                        {
                            "name": bt,
                            "layer": LAYER_IDENTITY,
                            "weight": 1.0,
                        }
                    )

        return char_tags_data

    def _build_char_occupied_groups(self, char_tags_data: list[dict]) -> set[str]:
        """Identify exclusive semantic groups occupied by character tags."""
        names = [ct["name"].lower().replace(" ", "_").strip() for ct in char_tags_data]
        if not names:
            return set()

        info_map = self.get_tag_info(names)
        return {info["group_name"] for info in info_map.values() if info.get("group_name") in EXCLUSIVE_GROUPS}

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
        Returns the set of occupied exclusive groups.
        """
        # 5. Distribute character tags
        for ct in char_tags_data:
            token = ct["name"]
            if ct["weight"] != 1.0:
                token = f"({token}:{ct['weight']})"
            layers[ct["layer"]].append(token)

        # 5b. Build character-occupied exclusive groups
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

    def _inject_loras(
        self,
        character: Character,
        scene_tags: list[str],
        layers: list[list[str]],
        style_loras: list[dict] | None,
    ) -> None:
        """Inject character LoRAs, scene-triggered LoRAs, and style LoRAs."""
        active_loras: dict[str, tuple[float, str | None]] = {}

        # Character LoRAs (style-type skipped; StyleProfile is SSOT for style)
        if character.loras and character.prompt_mode != "standard":
            for lora_info in character.loras:
                lora_id = lora_info.get("lora_id")
                weight = lora_info.get("weight")
                lora_obj = self.db.query(LoRA).filter(LoRA.id == lora_id).first()
                if lora_obj:
                    if lora_obj.lora_type == "style":
                        continue  # StyleProfile handles style LoRAs uniformly
                    if weight is None:
                        weight = self.get_effective_lora_weight(lora_obj)
                    active_loras[lora_obj.name] = (weight, lora_obj.lora_type)
                    for trigger in lora_obj.trigger_words or []:
                        if trigger not in layers[LAYER_IDENTITY]:
                            layers[LAYER_IDENTITY].append(trigger)

        # Scene-triggered LoRAs
        for tag in scene_tags:
            lora_name = LoRATriggerCache.get_lora_name(tag)
            if lora_name and lora_name not in active_loras:
                active_loras[lora_name] = self._get_lora_info(lora_name)

        # Inject LoRA tags into layers
        for name, (weight, lora_type) in active_loras.items():
            target_layer = LAYER_ATMOSPHERE if lora_type == "style" else LAYER_IDENTITY
            layers[target_layer].append(f"<lora:{name}:{self._cap_lora_weight(weight)}>")

        # Style LoRAs (explicit overrides)
        if style_loras:
            for lora_info in style_loras:
                name: str = lora_info.get("name", "")
                if name in active_loras:
                    continue  # Already injected via scene-triggered detection
                weight = lora_info.get("weight")
                if weight is None:
                    weight = self.get_lora_weight_by_name(name)
                for trigger in lora_info.get("trigger_words", []):
                    if trigger not in layers[LAYER_ATMOSPHERE]:
                        layers[LAYER_ATMOSPHERE].append(trigger)
                layers[LAYER_ATMOSPHERE].append(f"<lora:{name}:{self._cap_lora_weight(weight)}>")

    @staticmethod
    def _ensure_quality_tags(layers: list[list[str]]) -> None:
        """Ensure masterpiece and best_quality are in the quality layer."""
        quality_tokens = {t.lower().strip("() ").split(":")[0] for t in layers[LAYER_QUALITY]}
        if "masterpiece" not in quality_tokens:
            layers[LAYER_QUALITY].insert(0, "masterpiece")
        if "best_quality" not in quality_tokens:
            idx = 1 if "masterpiece" in quality_tokens or layers[LAYER_QUALITY] else 0
            layers[LAYER_QUALITY].insert(idx, "best_quality")

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

        # Style LoRA Unification: Collect style_loras names first for dedup
        # StyleProfile LoRAs take precedence over character LoRAs
        style_lora_names = {lora["name"] for lora in (style_loras or [])}

        if character_loras:
            for lora in character_loras:
                lora_name = lora["name"]
                # Dedup: skip if same LoRA is in style_loras (StyleProfile takes precedence)
                if lora_name in style_lora_names:
                    continue

                for trigger in lora.get("trigger_words", []):
                    if trigger not in layers[LAYER_IDENTITY]:
                        layers[LAYER_IDENTITY].append(trigger)

                weight = lora.get("weight")
                if weight is None:
                    weight = self.get_lora_weight_by_name(lora_name)
                layers[LAYER_IDENTITY].append(f"<lora:{lora_name}:{self._cap_lora_weight(weight)}>")

        # Auto-triggered LoRAs from tags
        for tag in tags:
            lora_name = LoRATriggerCache.get_lora_name(tag)
            if lora_name:
                # Skip if already in style_loras (StyleProfile precedence)
                if lora_name in style_lora_names:
                    continue
                already_present = any(
                    f"<lora:{lora_name}:" in t for t in (layers[LAYER_IDENTITY] + layers[LAYER_ATMOSPHERE])
                )
                if not already_present:
                    weight, lora_type = self._get_lora_info(lora_name)
                    target = LAYER_ATMOSPHERE if lora_type == "style" else LAYER_IDENTITY
                    layers[target].append(f"<lora:{lora_name}:{self._cap_lora_weight(weight)}>")

        if style_loras:
            for lora in style_loras:
                for trigger in lora.get("trigger_words", []):
                    if trigger not in layers[LAYER_ATMOSPHERE]:
                        layers[LAYER_ATMOSPHERE].append(trigger)

                weight = lora.get("weight")
                if weight is None:
                    weight = self.get_lora_weight_by_name(lora["name"])
                layers[LAYER_ATMOSPHERE].append(f"<lora:{lora['name']}:{self._cap_lora_weight(weight)}>")

        # Background scene defense: strip character layers after all LoRA injection
        if self._is_background_scene(tags):
            self._strip_character_layers(layers)

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

    # Male enhancement tags (Danbooru standard) to counter SD female bias
    _MALE_INDICATORS = frozenset({"1boy", "2boys", "3boys", "male", "man", "boy"})
    _FEMALE_INDICATORS = frozenset({"1girl", "2girls", "3girls", "female", "woman", "girl"})
    _MALE_ENHANCEMENT = ["(1boy:1.3)", "(male_focus:1.2)", "(bishounen:1.1)"]

    def _apply_gender_enhancement(
        self, character: "Character", char_tags_data: list[dict], layers: list[list[str]]
    ) -> None:
        """Add male enhancement tags if character is male (SD model bias fix)."""
        gender = (character.gender or "").lower()
        if not gender:
            all_names = {ct["name"].lower().strip("()").split(":")[0] for ct in char_tags_data}
            for token in list(all_names) + [t.lower() for t in (layers[LAYER_SUBJECT] + layers[LAYER_IDENTITY])]:
                if token in self._MALE_INDICATORS:
                    gender = "male"
                    break
                if token in self._FEMALE_INDICATORS:
                    gender = "female"
                    break

        if gender == "male":
            for tag in self._MALE_ENHANCEMENT:
                if tag not in layers[LAYER_SUBJECT]:
                    layers[LAYER_SUBJECT].append(tag)

    @staticmethod
    def _dedup_key(token: str) -> str:
        """Normalize token for dedup: strip weight parens e.g. (1boy:1.3) → 1boy."""
        t = token.strip().lower()
        if t.startswith("(") and ":" in t and t.endswith(")"):
            t = t[1:].split(":")[0]
        return t

    def _flatten_layers(self, layers: list[list[str]]) -> str:
        """Flattens 12 layers into a final string with global deduplication and conflict resolution."""
        TagRuleCache.initialize(self.db)

        final_tokens = []
        global_seen: set[str] = set()

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

                # Layer 7, 8 (Expression, Action) weight boost
                if i in [LAYER_EXPRESSION, LAYER_ACTION]:
                    unique_layer_tokens = [f"({t}:1.1)" if ":" not in t else t for t in unique_layer_tokens]

                final_tokens.extend(unique_layer_tokens)

        return ", ".join(final_tokens)

    def get_effective_lora_weight(self, lora: LoRA) -> float:
        """Helper to get calibrated weight from LoRA object."""
        if lora.optimal_weight is not None:
            return float(lora.optimal_weight)
        if lora.default_weight is not None:
            return float(lora.default_weight)
        return 0.7

    def _get_lora_info(self, name: str) -> tuple[float, str | None]:
        """Looks up LoRA weight and type by name with caching."""
        if name in self._lora_info_cache:
            return self._lora_info_cache[name]

        lora = self.db.query(LoRA).filter(LoRA.name == name).first()
        if not lora:
            info = (0.7, None)
        else:
            info = (self.get_effective_lora_weight(lora), lora.lora_type)

        self._lora_info_cache[name] = info
        return info

    def get_lora_weight_by_name(self, name: str) -> float:
        """Looks up LoRA weight by name with caching."""
        weight, _ = self._get_lora_info(name)
        return weight

    # ── Conflict resolution ──────────────────────────────────────────────

    _OUTDOOR_TAGS = frozenset(
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
    _INDOOR_TAGS = frozenset(
        {
            "indoors",
            "room",
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
        }
    )

    _CAMERA_WIDE = frozenset({"full_body", "wide_shot"})
    _CAMERA_MID = frozenset({"cowboy_shot", "upper_body", "from_waist"})
    _CAMERA_CLOSE = frozenset({"close-up", "close_up", "portrait", "face", "headshot"})

    def _resolve_location_conflicts(self, env_tokens: list[str]) -> list[str]:
        """Remove conflicting location tags from the environment layer."""
        if not env_tokens:
            return env_tokens

        outdoor_found = []
        indoor_found = []
        neutral = []

        for token in env_tokens:
            norm = token.lower().replace(" ", "_").strip()
            if norm in self._OUTDOOR_TAGS:
                outdoor_found.append(token)
            elif norm in self._INDOOR_TAGS:
                indoor_found.append(token)
            else:
                neutral.append(token)

        if outdoor_found and indoor_found:
            winner = outdoor_found if len(outdoor_found) >= len(indoor_found) else indoor_found
        else:
            winner = outdoor_found + indoor_found

        generic = {"indoors", "outdoors"}
        specific = []
        generic_tags = []
        for token in winner:
            norm = token.lower().replace(" ", "_").strip()
            if norm in generic:
                generic_tags.append(token)
            elif not specific:
                specific.append(token)

        return specific + generic_tags + neutral

    def _resolve_camera_conflicts(self, cam_tokens: list[str]) -> list[str]:
        """Keep only one framing tag when conflicts exist."""
        if not cam_tokens:
            return cam_tokens

        all_camera = self._CAMERA_WIDE | self._CAMERA_MID | self._CAMERA_CLOSE
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


def get_v3_prompt_builder():
    db = SessionLocal()
    try:
        yield V3PromptBuilder(db)
    finally:
        db.close()
