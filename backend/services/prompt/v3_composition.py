"""Pure V3 Prompt Composition Service with 12-Layer System."""

from sqlalchemy.orm import Session

from database import SessionLocal
from models.character import Character
from models.lora import LoRA
from models.tag import Tag
from services.keywords.db_cache import LoRATriggerCache

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

        # 1. Collect Character tags and their metadata from relationships
        char_tags_data = []
        for char_tag in character.tags:
            tag = char_tag.tag
            char_tags_data.append({
                "name": tag.name,
                "layer": LAYER_IDENTITY if char_tag.is_permanent else tag.default_layer,
                "weight": char_tag.weight
            })

        # 2. Get Scene tag info
        scene_tag_info = self.get_tag_info(scene_tags)

        # 3. Initialize 12 layers
        layers: list[list[str]] = [[] for _ in range(12)]

        # 4. Distribute Character Tags
        for ct in char_tags_data:
            token = ct["name"]
            if ct["weight"] != 1.0:
                token = f"({token}:{ct['weight']})"
            layers[ct["layer"]].append(token)

        # 5. Distribute Scene Tags
        for tag in scene_tags:
            norm_tag = tag.lower().replace(" ", "_").strip()
            info = scene_tag_info.get(norm_tag, {"layer": LAYER_SUBJECT})
            layers[info["layer"]].append(tag)

        # 6. Inject Character LoRAs & Triggers
        # Character explicitly defined LoRAs
        active_loras: dict[str, float] = {} # name -> weight

        if character.loras and character.prompt_mode != "standard":
            for lora_info in character.loras:
                lora_id = lora_info.get("lora_id")
                weight = lora_info.get("weight") # Explicit weight from character settings

                lora_obj = self.db.query(LoRA).filter(LoRA.id == lora_id).first()
                if lora_obj:
                    if weight is None:
                        weight = self.get_effective_lora_weight(lora_obj)

                    active_loras[lora_obj.name] = weight
                    # Triggers go to Identity layer
                    for trigger in (lora_obj.trigger_words or []):
                        if trigger not in layers[LAYER_IDENTITY]:
                            layers[LAYER_IDENTITY].append(trigger)

        # 7. Collect Triggered LoRAs from Scene Tags
        for tag in scene_tags:
            lora_name = LoRATriggerCache.get_lora_name(tag)
            if lora_name and lora_name not in active_loras:
                # Resolve calibrated weight
                active_loras[lora_name] = self.get_lora_weight_by_name(lora_name)

        # 8. Inject LoRA Tags into Layers
        for name, weight in active_loras.items():
            # For now, put all triggered LoRAs into IDENTITY layer
            # (In future, style LoRAs could go to ATMOSPHERE)
            layers[LAYER_IDENTITY].append(f"<lora:{name}:{weight}>")

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

        # 10. Add Quality Tags to Layer 0
        if not layers[LAYER_QUALITY]:
            layers[LAYER_QUALITY] = ["masterpiece", "best_quality"]

        return self._flatten_layers(layers, has_character_lora=bool(active_loras))

    def compose(
        self,
        tags: list[str],
        character_loras: list[dict] | None = None,
        style_loras: list[dict] | None = None,
    ) -> str:
        """Generic composition without direct DB character object."""
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

        if not layers[LAYER_QUALITY]:
            layers[LAYER_QUALITY] = ["masterpiece", "best_quality"]

        return self._flatten_layers(layers, has_character_lora=bool(character_loras))

    def _flatten_layers(self, layers: list[list[str]], has_character_lora: bool = False) -> str:
        """Flattens 12 layers into a final string with deduplication and BREAK."""
        final_tokens = []
        for i, layer_tokens in enumerate(layers):
            if layer_tokens:
                seen = set()
                unique_layer_tokens = []
                for t in layer_tokens:
                    if t.lower() not in seen:
                        unique_layer_tokens.append(t)
                        seen.add(t.lower())

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

    def _resolve_lora_placeholders(self, tokens: list[str]) -> list[str]:
        """Finds <lora:NAME> (without weight) and injects calibrated value."""
        resolved = []
        for t in tokens:
            if t.startswith("<lora:") and t.endswith(">"):
                # Check if it has weight (contains second colon)
                content = t[6:-1] # name[:weight]
                parts = content.split(":")

                if len(parts) == 1:
                    # Missing weight! Resolve it.
                    name = parts[0]
                    weight = self.get_lora_weight_by_name(name)
                    resolved.append(f"<lora:{name}:{weight}>")
                    continue

            resolved.append(t)
        return resolved

def get_v3_prompt_builder():
    db = SessionLocal()
    try:
        yield V3PromptBuilder(db)
    finally:
        db.close()
