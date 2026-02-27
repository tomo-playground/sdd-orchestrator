"""Multi-Character Prompt Composer for 2-person scenes.

Combines two characters' identity tags into a single prompt using
Character-Scoped Flattening + Trigger Prompt strategy.
Does NOT modify V3PromptBuilder._flatten_layers().
"""

from models.character import Character
from models.lora import LoRA
from services.prompt.v3_composition import (
    LAYER_ATMOSPHERE,
    LAYER_CAMERA,
    LAYER_ENVIRONMENT,
    LAYER_IDENTITY,
    LAYER_QUALITY,
    LAYER_SUBJECT,
    V3PromptBuilder,
)

# Wide framing preferred for multi-character scenes
_WIDE_FRAMING_TAGS = frozenset({"wide_shot", "upper_body"})
_CLOSE_FRAMING_TAGS = frozenset({"close-up", "close_up", "portrait", "headshot", "face"})


class MultiCharacterComposer:
    """2인 동시 출연 씬의 프롬프트 합성."""

    def __init__(self, builder: V3PromptBuilder):
        self.builder = builder

    def compose(
        self,
        char_a: Character,
        char_b: Character,
        scene_tags: list[str],
        style_loras: list[dict] | None = None,
        scene_character_actions: list[dict] | None = None,
        quality_tags: list[str] | None = None,
    ) -> str:
        """Compose prompt for a 2-character scene."""
        scene_tags = self.builder._resolve_aliases(scene_tags)

        # 1. Build subject layer
        subject = self._build_subject(char_a, char_b)

        # 2. Collect each character's tags independently
        char_a_tags = self.builder._collect_character_tags(char_a)
        char_b_tags = self.builder._collect_character_tags(char_b)

        # 3. Build per-character layers and flatten
        char_a_flat = self._flatten_character(char_a, char_a_tags, scene_character_actions)
        char_b_flat = self._flatten_character(char_b, char_b_tags, scene_character_actions)

        # 4. Scene tags → layers (environment, camera, atmosphere only)
        scene_flat = self._flatten_scene_tags(scene_tags)

        # 5. Quality (explicit > extracted from scene_tags > fallback) + LoRAs
        effective_quality = quality_tags or self._extract_quality_tags(scene_tags)
        if effective_quality:
            quality = ", ".join(effective_quality)
        else:
            from config import FALLBACK_QUALITY_TAGS

            quality = ", ".join(FALLBACK_QUALITY_TAGS)
        lora_str = self._build_lora_string(char_a, char_b, style_loras)

        # 6. Prefer wide framing for multi-char
        scene_flat = self._enforce_wide_framing(scene_flat)

        parts = [p for p in [quality, subject, char_a_flat, char_b_flat, scene_flat, lora_str] if p]
        raw = ", ".join(parts)

        # Global dedup across characters (e.g. chibi on both chars)
        seen: set[str] = set()
        deduped: list[str] = []
        for token in (t.strip() for t in raw.split(",")):
            if not token:
                continue
            key = V3PromptBuilder._dedup_key(token)
            if key not in seen:
                deduped.append(token)
                seen.add(key)
        return ", ".join(deduped)

    def _build_subject(self, char_a: Character, char_b: Character) -> str:
        """Build subject layer: trigger prompt or gender-based fallback."""
        # Check LoRAs for multi_char_trigger_prompt
        trigger = self._find_trigger_prompt(char_a) or self._find_trigger_prompt(char_b)
        if trigger:
            return trigger

        ga = (char_a.gender or "").lower()
        gb = (char_b.gender or "").lower()
        return self._gender_tags(ga, gb)

    def _find_trigger_prompt(self, character: Character) -> str | None:
        """Find multi_char_trigger_prompt from character's LoRAs."""
        if not character.loras:
            return None
        for lora_info in character.loras:
            lora_obj = self.builder.db.query(LoRA).filter(LoRA.id == lora_info.get("lora_id")).first()
            if lora_obj and lora_obj.multi_char_trigger_prompt:
                return lora_obj.multi_char_trigger_prompt
        return None

    @staticmethod
    def _gender_tags(ga: str, gb: str) -> str:
        """Generate gender subject tags from two genders."""
        genders = sorted([ga or "female", gb or "female"])
        if genders == ["female", "male"]:
            return "1boy, 1girl"
        if genders == ["female", "female"]:
            return "2girls"
        if genders == ["male", "male"]:
            return "2boys"
        return "1boy, 1girl"  # fallback

    def _flatten_character(self, character: Character, char_tags: list[dict], actions: list[dict] | None) -> str:
        """Flatten a single character's tags into comma-separated string."""
        layers: list[list[str]] = [[] for _ in range(12)]
        for ct in char_tags:
            token = ct["name"]
            if ct["weight"] != 1.0:
                token = f"({token}:{ct['weight']})"
            layers[ct["layer"]].append(token)

        if actions:
            self.builder._apply_scene_character_actions(character.id, actions, layers)

        # Collect only identity/body/cloth/accessory/expression/action layers
        tokens = []
        for i in range(LAYER_IDENTITY, LAYER_CAMERA):
            tokens.extend(layers[i])
        return ", ".join(tokens) if tokens else ""

    def _extract_quality_tags(self, scene_tags: list[str]) -> list[str]:
        """Extract LAYER_QUALITY tags from scene_tags (e.g. StyleProfile quality)."""
        tag_info = self.builder.get_tag_info(scene_tags)
        quality = []
        for tag in scene_tags:
            if tag.strip().startswith("<lora:"):
                continue
            norm = tag.lower().replace(" ", "_").strip()
            info = tag_info.get(norm, {"layer": LAYER_SUBJECT})
            if info["layer"] == LAYER_QUALITY:
                quality.append(tag)
        return quality

    def _flatten_scene_tags(self, scene_tags: list[str]) -> str:
        """Flatten scene tags (environment, camera, atmosphere only)."""
        tag_info = self.builder.get_tag_info(scene_tags)
        scene_layers = {LAYER_CAMERA, LAYER_ENVIRONMENT, LAYER_ATMOSPHERE}
        tokens = []
        for tag in scene_tags:
            if tag.strip().startswith("<lora:"):
                continue
            norm = tag.lower().replace(" ", "_").strip()
            info = tag_info.get(norm, {"layer": LAYER_SUBJECT})
            if info["layer"] in scene_layers:
                tokens.append(tag)
        return ", ".join(tokens) if tokens else ""

    def _build_lora_string(self, char_a: Character, char_b: Character, style_loras: list[dict] | None) -> str:
        """Build LoRA injection string with dedup and weight scaling."""
        injected: dict[str, str] = {}  # name -> lora_tag

        # Character LoRAs
        for char in [char_a, char_b]:
            self._inject_character_loras(char, injected)

        # Style LoRAs (dedup)
        if style_loras:
            for lora in style_loras:
                name = lora.get("name", "")
                if name in injected:
                    continue
                weight = lora.get("weight") or self.builder.get_lora_weight_by_name(name)
                weight = V3PromptBuilder._cap_lora_weight(weight)
                injected[name] = f"<lora:{name}:{weight}>"

        return ", ".join(injected.values()) if injected else ""

    def _inject_character_loras(self, character: Character, injected: dict[str, str]) -> None:
        """Inject a character's LoRAs with multi_char_weight_scale applied."""
        if not character.loras:
            return
        for lora_info in character.loras:
            lora_obj = self.builder.db.query(LoRA).filter(LoRA.id == lora_info.get("lora_id")).first()
            if not lora_obj or lora_obj.lora_type == "style":
                continue
            if lora_obj.name in injected:
                continue
            weight = lora_info.get("weight") or self.builder.get_effective_lora_weight(lora_obj)
            # Apply multi_char_weight_scale
            if lora_obj.multi_char_weight_scale is not None:
                weight = round(float(weight) * float(lora_obj.multi_char_weight_scale), 2)
            weight = V3PromptBuilder._cap_lora_weight(float(weight))
            injected[lora_obj.name] = f"<lora:{lora_obj.name}:{weight}>"

    @staticmethod
    def _enforce_wide_framing(scene_flat: str) -> str:
        """Replace close-up framing with wide_shot for multi-char scenes."""
        if not scene_flat:
            return "wide_shot"
        tokens = [t.strip() for t in scene_flat.split(",")]
        has_wide = any(t.lower().replace(" ", "_") in _WIDE_FRAMING_TAGS for t in tokens)
        if has_wide:
            return scene_flat
        # Remove close framing, add wide_shot (has_wide=False guaranteed here)
        filtered = [t for t in tokens if t.lower().replace(" ", "_") not in _CLOSE_FRAMING_TAGS]
        filtered.insert(0, "wide_shot")
        return ", ".join(filtered)
