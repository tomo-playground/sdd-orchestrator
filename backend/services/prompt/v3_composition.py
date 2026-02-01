"""Pure V3 Prompt Composition Service with 12-Layer System."""

from sqlalchemy.orm import Session

from database import SessionLocal
from models.character import Character
from models.lora import LoRA
from models.tag import Tag
from services.keywords.db_cache import LoRATriggerCache, TagAliasCache

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


class V3PromptBuilder:
    """Prompt builder using the 12-layer semantic staking system."""

    def __init__(self, db: Session):
        self.db = db
        self._lora_weight_cache: dict[str, float] = {}

    def get_tag_info(self, tag_names: list[str]) -> dict[str, dict]:
        """Fetches metadata for a list of tags from the DB."""
        if not tag_names:
            return {}

        # Normalize tags for DB lookup
        normalized_names = [t.lower().replace(" ", "_").strip() for t in tag_names]

        tags = self.db.query(Tag).filter(Tag.name.in_(normalized_names)).all()
        return {tag.name: {"layer": tag.default_layer, "scope": tag.usage_scope} for tag in tags}

    def compose_for_character(
        self,
        character_id: int,
        scene_tags: list[str],
        style_loras: list[dict] | None = None,
    ) -> str:
        """Composes a prompt specifically for a Character project."""
        character = self.db.query(Character).filter(Character.id == character_id).first()
        if not character:
            return self.compose(scene_tags, style_loras=style_loras)

        # 1. Collect Character tags (is_permanent = always include, layer from default_layer)
        char_tags_data = []
        for char_tag in character.tags:
            tag = char_tag.tag
            char_tags_data.append({
                "name": tag.name,
                "layer": tag.default_layer,
                "weight": char_tag.weight
            })

        # 2. Add Custom Base Prompt (Identity)
        restricted = ["background", "kitchen", "room", "outdoors", "indoors", "scenery", "nature", "mountain", "street", "office", "bedroom", "bathroom", "garden"]
        if character.custom_base_prompt:
            base_tokens = [t.strip() for t in character.custom_base_prompt.split(",")]
            for bt in base_tokens:
                if any(r in bt.lower() for r in restricted):
                    continue # Skip background/situation tags in Identity DNA
                if bt:
                    char_tags_data.append({
                        "name": bt,
                        "layer": LAYER_IDENTITY,
                        "weight": 1.0
                    })

        # 2. Resolve aliases in scene tags
        scene_tags = self._resolve_aliases(scene_tags)

        # 3. Get Scene tag info
        scene_tag_info = self.get_tag_info(scene_tags)

        # 4. Initialize 12 layers
        layers: list[list[str]] = [[] for _ in range(12)]

        # 5. Distribute Character Tags
        for ct in char_tags_data:
            token = ct["name"]
            if ct["weight"] != 1.0:
                token = f"({token}:{ct['weight']})"
            layers[ct["layer"]].append(token)

        # 6. Distribute Scene Tags
        for tag in scene_tags:
            norm_tag = tag.lower().replace(" ", "_").strip()
            info = scene_tag_info.get(norm_tag, {"layer": LAYER_SUBJECT})
            layers[info["layer"]].append(tag)

        # 6. Inject Character LoRAs & Triggers
        # active_loras: name -> (weight, lora_type)
        active_loras: dict[str, tuple[float, str | None]] = {}

        if character.loras and character.prompt_mode != "standard":
            for lora_info in character.loras:
                lora_id = lora_info.get("lora_id")
                weight = lora_info.get("weight")

                lora_obj = self.db.query(LoRA).filter(LoRA.id == lora_id).first()
                if lora_obj:
                    if weight is None:
                        weight = self.get_effective_lora_weight(lora_obj)

                    active_loras[lora_obj.name] = (weight, lora_obj.lora_type)
                    trigger_layer = LAYER_ATMOSPHERE if lora_obj.lora_type == "style" else LAYER_IDENTITY
                    for trigger in (lora_obj.trigger_words or []):
                        if trigger not in layers[trigger_layer]:
                            layers[trigger_layer].append(trigger)

        # 7. Collect Triggered LoRAs from Scene Tags
        for tag in scene_tags:
            lora_name = LoRATriggerCache.get_lora_name(tag)
            if lora_name and lora_name not in active_loras:
                active_loras[lora_name] = (self.get_lora_weight_by_name(lora_name), None)

        # 8. Inject LoRA Tags into Layers (character→L2, style→L11)
        for name, (weight, lora_type) in active_loras.items():
            target_layer = LAYER_ATMOSPHERE if lora_type == "style" else LAYER_IDENTITY
            layers[target_layer].append(f"<lora:{name}:{weight}>")

        # 9. Inject Style LoRAs (Atmosphere) - These are explicit overrides
        if style_loras:
            for lora_info in style_loras:
                name = lora_info.get("name")
                weight = lora_info.get("weight")
                if weight is None:
                    weight = self.get_lora_weight_by_name(name)

                triggers = lora_info.get("trigger_words", [])
                for trigger in triggers:
                    if trigger not in layers[LAYER_ATMOSPHERE]:
                        layers[LAYER_ATMOSPHERE].append(trigger)
                layers[LAYER_ATMOSPHERE].append(f"<lora:{name}:{weight}>")

        # 10. Gender enhancement for male characters (SD model bias)
        self._apply_gender_enhancement(character, char_tags_data, layers)

        # 11. Resolve location conflicts in ENVIRONMENT layer
        layers[LAYER_ENVIRONMENT] = self._resolve_location_conflicts(
            layers[LAYER_ENVIRONMENT]
        )

        # 11b. Resolve camera conflicts in CAMERA layer
        layers[LAYER_CAMERA] = self._resolve_camera_conflicts(
            layers[LAYER_CAMERA]
        )

        # 12. Ensure Quality Tags in Layer 0
        quality_tokens = {t.lower().strip("() ").split(":")[0] for t in layers[LAYER_QUALITY]}
        if "masterpiece" not in quality_tokens:
            layers[LAYER_QUALITY].insert(0, "masterpiece")
        if "best_quality" not in quality_tokens:
            idx = 1 if "masterpiece" in quality_tokens or layers[LAYER_QUALITY] else 0
            layers[LAYER_QUALITY].insert(idx, "best_quality")

        return self._flatten_layers(layers, has_character_lora=bool(active_loras))

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

        if character_loras:
            for lora in character_loras:
                # Triggers
                for trigger in lora.get("trigger_words", []):
                    if trigger not in layers[LAYER_IDENTITY]:
                        layers[LAYER_IDENTITY].append(trigger)

                # LoRA tag logic
                weight = lora.get("weight")
                if weight is None:
                    # Resolve from name
                    weight = self.get_lora_weight_by_name(lora["name"])

                layers[LAYER_IDENTITY].append(f"<lora:{lora['name']}:{weight}>")

        # Auto-triggered LoRAs from tags
        for tag in tags:
            lora_name = LoRATriggerCache.get_lora_name(tag)
            if lora_name:
                # Check if already added
                already_present = any(f"<lora:{lora_name}:" in t for t in (layers[LAYER_IDENTITY] + layers[LAYER_ATMOSPHERE]))
                if not already_present:
                    weight = self.get_lora_weight_by_name(lora_name)
                    layers[LAYER_IDENTITY].append(f"<lora:{lora_name}:{weight}>")

        if style_loras:
            for lora in style_loras:
                # Triggers
                for trigger in lora.get("trigger_words", []):
                    if trigger not in layers[LAYER_ATMOSPHERE]:
                        layers[LAYER_ATMOSPHERE].append(trigger)

                # LoRA tag logic
                weight = lora.get("weight")
                if weight is None:
                    weight = self.get_lora_weight_by_name(lora["name"])

                layers[LAYER_ATMOSPHERE].append(f"<lora:{lora['name']}:{weight}>")

        # Resolve location conflicts
        layers[LAYER_ENVIRONMENT] = self._resolve_location_conflicts(
            layers[LAYER_ENVIRONMENT]
        )

        # Resolve camera conflicts
        layers[LAYER_CAMERA] = self._resolve_camera_conflicts(
            layers[LAYER_CAMERA]
        )

        quality_tokens = {t.lower().strip("() ").split(":")[0] for t in layers[LAYER_QUALITY]}
        if "masterpiece" not in quality_tokens:
            layers[LAYER_QUALITY].insert(0, "masterpiece")
        if "best_quality" not in quality_tokens:
            idx = 1 if "masterpiece" in quality_tokens or layers[LAYER_QUALITY] else 0
            layers[LAYER_QUALITY].insert(idx, "best_quality")

        return self._flatten_layers(layers, has_character_lora=bool(character_loras))

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
        # Detect gender from character DB field, custom_base_prompt, or tags
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
        # Strip weight syntax: (tag:weight) → tag
        if t.startswith("(") and ":" in t and t.endswith(")"):
            t = t[1:].split(":")[0]
        return t

    def _flatten_layers(self, layers: list[list[str]], has_character_lora: bool = False) -> str:
        """Flattens 12 layers into a final string with global deduplication and BREAK."""
        final_tokens = []
        global_seen: set[str] = set()  # Cross-layer deduplication

        for i, layer_tokens in enumerate(layers):
            if layer_tokens:
                unique_layer_tokens = []
                for t in layer_tokens:
                    key = self._dedup_key(t)
                    if key not in global_seen:
                        unique_layer_tokens.append(t)
                        global_seen.add(key)

                # Layer 7, 8 (Expression, Action) weight boost
                if i in [LAYER_EXPRESSION, LAYER_ACTION]:
                    unique_layer_tokens = [
                        f"({t}:1.1)" if ":" not in t else t
                        for t in unique_layer_tokens
                    ]

                final_tokens.extend(unique_layer_tokens)

            # BREAK after Layer 6 (Accessory) if character LoRA is used
            # This must trigger even if layer 6 is empty
            if i == LAYER_ACCESSORY and has_character_lora:
                if final_tokens and final_tokens[-1] != "BREAK":
                    final_tokens.append("BREAK")

        return ", ".join(final_tokens)

    def get_effective_lora_weight(self, lora: LoRA) -> float:
        """Helper to get calibrated weight from LoRA object."""
        if lora.optimal_weight is not None:
            return float(lora.optimal_weight)
        if lora.default_weight is not None:
            return float(lora.default_weight)
        return 0.7

    def get_lora_weight_by_name(self, name: str) -> float:
        """Looks up LoRA weight by name with caching."""
        if name in self._lora_weight_cache:
            return self._lora_weight_cache[name]

        lora = self.db.query(LoRA).filter(LoRA.name == name).first()
        if not lora:
            weight = 0.7
        else:
            weight = self.get_effective_lora_weight(lora)

        self._lora_weight_cache[name] = weight
        return weight

    # Location tag groups for conflict resolution
    _OUTDOOR_TAGS = frozenset({
        "outdoors", "street", "park", "forest", "beach", "mountain",
        "garden", "city", "field", "lake", "river", "rooftop",
    })
    _INDOOR_TAGS = frozenset({
        "indoors", "room", "bedroom", "kitchen", "bathroom", "classroom",
        "library", "office", "cafe", "school", "hospital", "church",
        "restaurant", "shop", "hallway", "living_room",
    })

    # Camera tags that conflict with each other (only one framing allowed)
    _CAMERA_WIDE = frozenset({"full_body", "wide_shot"})
    _CAMERA_MID = frozenset({"cowboy_shot", "upper_body", "from_waist"})
    _CAMERA_CLOSE = frozenset({"close-up", "close_up", "portrait", "face", "headshot"})

    def _resolve_location_conflicts(self, env_tokens: list[str]) -> list[str]:
        """Remove conflicting location tags from the environment layer.

        1. Indoor vs outdoor conflict: keep the majority group.
        2. Same-category dedup: keep only the first specific location.
           Generic tags (indoors/outdoors) are kept as-is.
        """
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

        # Resolve indoor vs outdoor conflict
        if outdoor_found and indoor_found:
            if len(outdoor_found) >= len(indoor_found):
                winner = outdoor_found
            else:
                winner = indoor_found
        else:
            winner = outdoor_found + indoor_found

        # Limit to 1 specific location + generic tag (indoors/outdoors)
        generic = {"indoors", "outdoors"}
        specific = []
        generic_tags = []
        for token in winner:
            norm = token.lower().replace(" ", "_").strip()
            if norm in generic:
                generic_tags.append(token)
            elif not specific:  # Keep only first specific location
                specific.append(token)

        return specific + generic_tags + neutral

    def _resolve_camera_conflicts(self, cam_tokens: list[str]) -> list[str]:
        """Keep only one framing tag when conflicts exist.

        Priority: first tag wins. Removes conflicting framing tags.
        """
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
                # Skip subsequent conflicting framing tags
            else:
                result.append(token)

        return result


def get_v3_prompt_builder():
    db = SessionLocal()
    try:
        yield V3PromptBuilder(db)
    finally:
        db.close()
