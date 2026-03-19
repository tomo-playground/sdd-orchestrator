"""Multi-Character Prompt Composer for 2-person scenes.

Combines two characters' identity tags into a single prompt using
BREAK-token separation for cross-attention isolation.
Does NOT modify PromptBuilder._flatten_layers().
"""

import logging

from config import MULTI_CHAR_MAX_TOTAL_LORA_WEIGHT, SCENE_CHARACTER_LORA_SCALE
from models.character import Character
from services.prompt.composition import (
    LAYER_ATMOSPHERE,
    LAYER_CAMERA,
    LAYER_ENVIRONMENT,
    LAYER_IDENTITY,
    LAYER_QUALITY,
    LAYER_SUBJECT,
    PromptBuilder,
)

logger = logging.getLogger(__name__)

# Wide framing preferred for multi-character scenes
_WIDE_FRAMING_TAGS = frozenset({"wide_shot", "upper_body"})
_CLOSE_FRAMING_TAGS = frozenset({"close-up", "close_up", "portrait", "headshot", "face"})

# 멀티캐릭터 씬에서 금지할 태그
_MULTI_BANNED_TAGS = frozenset({"solo"})

# 상호작용 태그 (Gemini 가 하나도 안 넣었을 때 기본 주입)
_INTERACTION_TAGS = frozenset(
    {
        "eye_contact",
        "facing_another",
        "holding_hands",
        "hugging",
        "carrying",
        "arm_in_arm",
    }
)


class MultiCharacterComposer:
    """2인 동시 출연 씬의 프롬프트 합성."""

    def __init__(self, builder: PromptBuilder):
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
        """Compose prompt for a 2-character scene.

        구조: "quality, subject, scene, lora BREAK charA BREAK charB"
        """
        scene_tags = self.builder._resolve_aliases(scene_tags)

        # 1. Build subject layer (성별 기반)
        subject = self._build_subject(char_a, char_b)

        # 2. Collect each character's tags independently
        char_a_tags = self.builder._collect_character_tags(char_a)
        char_b_tags = self.builder._collect_character_tags(char_b)

        # 3. Build per-character layers and flatten
        char_a_flat = self._flatten_character(char_a, char_a_tags, scene_character_actions)
        char_b_flat = self._flatten_character(char_b, char_b_tags, scene_character_actions)

        # 4. Scene tags -> layers (environment, camera, atmosphere only)
        scene_flat = self._flatten_scene_tags(scene_tags)

        # 5. Interaction 태그 기본 주입
        scene_flat = self._ensure_interaction_tag(scene_flat, scene_tags)

        # 6. Quality (explicit > extracted from scene_tags > fallback) + LoRAs
        effective_quality = quality_tags or self._extract_quality_tags(scene_tags)
        if effective_quality:
            quality = ", ".join(effective_quality)
        else:
            from config import FALLBACK_QUALITY_TAGS

            quality = ", ".join(FALLBACK_QUALITY_TAGS)
        lora_str = self._build_lora_string(char_a, char_b, style_loras)

        # 7. Prefer wide framing for multi-char
        scene_flat = self._enforce_wide_framing(scene_flat)

        # 8. 공통 부분 조합 + Per-BREAK dedup
        common_parts = [p for p in [quality, subject, scene_flat, lora_str] if p]
        common_raw = ", ".join(common_parts)
        common_deduped = self._dedup_tokens(common_raw)

        # Per-BREAK dedup (각 캐릭터 독립)
        char_a_deduped = self._dedup_tokens(char_a_flat)
        char_b_deduped = self._dedup_tokens(char_b_flat)

        # 9. BREAK 토큰으로 분리
        sections = [common_deduped]
        if char_a_deduped:
            sections.append(char_a_deduped)
        if char_b_deduped:
            sections.append(char_b_deduped)

        return "\nBREAK\n".join(sections)

    def _build_subject(self, char_a: Character, char_b: Character) -> str:
        """Build subject layer: 성별 기반으로만 동작."""
        ga = (char_a.gender or "").lower()
        gb = (char_b.gender or "").lower()
        return self._gender_tags(ga, gb)

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

        # Banned tags 제거
        filtered = [t for t in tokens if self._token_base(t) not in _MULTI_BANNED_TAGS]
        return ", ".join(filtered) if filtered else ""

    @staticmethod
    def _token_base(token: str) -> str:
        """Extract base tag name (strip weight/parens)."""
        t = token.strip().lstrip("(")
        t = t.split(":")[0].rstrip(")")
        return t.lower().replace(" ", "_")

    def _extract_quality_tags(self, scene_tags: list[str]) -> list[str]:
        """Extract LAYER_QUALITY tags from scene_tags."""
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

    def _ensure_interaction_tag(self, scene_flat: str, scene_tags: list[str]) -> str:
        """Interaction 태그가 하나도 없으면 facing_another 기본 삽입."""
        all_tags = set()
        for t in scene_tags:
            all_tags.add(t.lower().replace(" ", "_").strip())
        if scene_flat:
            for t in scene_flat.split(","):
                all_tags.add(t.strip().lower().replace(" ", "_"))

        if all_tags & _INTERACTION_TAGS:
            return scene_flat

        # 기본 interaction 태그 삽입
        if scene_flat:
            return f"facing_another, {scene_flat}"
        return "facing_another"

    def _build_lora_string(self, char_a: Character, char_b: Character, style_loras: list[dict] | None) -> str:
        """Build LoRA injection string with dedup and weight scaling."""
        char_loras: dict[str, tuple[str, float]] = {}  # name -> (lora_tag, weight)
        style_lora_tags: list[str] = []

        # Character LoRAs (weight 상한 적용 대상)
        for char in [char_a, char_b]:
            self._inject_character_loras(char, char_loras)

        # Style LoRAs (상한 제외, 개별 cap만 적용)
        if style_loras:
            for lora in style_loras:
                name = lora.get("name", "")
                if name in char_loras:
                    continue
                weight = lora.get("weight") or self.builder.get_lora_weight_by_name(name)
                weight = PromptBuilder._cap_lora_weight(weight)
                style_lora_tags.append(f"<lora:{name}:{weight}>")

        # Character LoRA만 합산 상한 검증
        capped = self._cap_total_lora_weight(char_loras) if char_loras else ""
        parts = [p for p in [capped, ", ".join(style_lora_tags)] if p]
        return ", ".join(parts)

    def _inject_character_loras(self, character: Character, injected: dict[str, tuple[str, float]]) -> None:
        """Inject a character's LoRAs with SCENE_CHARACTER_LORA_SCALE 적용."""
        if not character.loras:
            return
        from models.lora import LoRA

        for lora_info in character.loras:
            lora_obj = self.builder.db.query(LoRA).filter(LoRA.id == lora_info.get("lora_id")).first()
            if not lora_obj or lora_obj.lora_type == "style":
                continue
            if lora_obj.name in injected:
                continue
            weight = lora_info.get("weight") or self.builder.get_effective_lora_weight(lora_obj)
            # SCENE_CHARACTER_LORA_SCALE 적용 (멀티캐릭터 씬 공통 스케일)
            weight = round(float(weight) * SCENE_CHARACTER_LORA_SCALE, 2)
            weight = PromptBuilder._cap_lora_weight(float(weight))
            injected[lora_obj.name] = (f"<lora:{lora_obj.name}:{weight}>", float(weight))

    @staticmethod
    def _cap_total_lora_weight(injected: dict[str, tuple[str, float]]) -> str:
        """LoRA weight 합산이 상한 초과 시 비례 축소."""
        total = sum(w for _, w in injected.values())
        if total <= MULTI_CHAR_MAX_TOTAL_LORA_WEIGHT:
            return ", ".join(tag for tag, _ in injected.values())

        # 비례 축소
        scale = MULTI_CHAR_MAX_TOTAL_LORA_WEIGHT / total
        logger.warning(
            "[MultiChar] LoRA weight 합산 %.2f > 상한 %.2f, 비례 축소 (scale=%.2f)",
            total,
            MULTI_CHAR_MAX_TOTAL_LORA_WEIGHT,
            scale,
        )
        scaled_tags = []
        for name, (_, w) in injected.items():
            new_w = round(w * scale, 2)
            scaled_tags.append(f"<lora:{name}:{new_w}>")
        return ", ".join(scaled_tags)

    @staticmethod
    def _enforce_wide_framing(scene_flat: str) -> str:
        """Replace close-up framing with wide_shot for multi-char scenes."""
        if not scene_flat:
            return "wide_shot"
        tokens = [t.strip() for t in scene_flat.split(",")]
        has_wide = any(t.lower().replace(" ", "_") in _WIDE_FRAMING_TAGS for t in tokens)
        if has_wide:
            return scene_flat
        # Remove close framing, add wide_shot
        filtered = [t for t in tokens if t.lower().replace(" ", "_") not in _CLOSE_FRAMING_TAGS]
        filtered.insert(0, "wide_shot")
        return ", ".join(filtered)

    @staticmethod
    def _dedup_tokens(raw: str) -> str:
        """Dedup tokens within a single section."""
        if not raw:
            return ""
        seen: set[str] = set()
        deduped: list[str] = []
        for token in (t.strip() for t in raw.split(",")):
            if not token:
                continue
            key = PromptBuilder._dedup_key(token)
            if key not in seen:
                deduped.append(token)
                seen.add(key)
        return ", ".join(deduped)
