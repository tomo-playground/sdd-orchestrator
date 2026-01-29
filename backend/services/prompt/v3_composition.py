"""Pure V3 Prompt Composition Service with 12-Layer System."""

import re
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from models.tag import Tag
from models.lora import LoRA
from models.character import Character
from database import SessionLocal

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

    def get_tag_info(self, tag_names: List[str]) -> Dict[str, Dict]:
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
        scene_tags: List[str],
        style_loras: Optional[List[Dict]] = None,
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
        layers: List[List[str]] = [[] for _ in range(12)]
        
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
        # prompt_mode: auto, standard, lora
        use_lora = True
        if character.prompt_mode == "standard":
            use_lora = False
        elif character.prompt_mode == "auto":
            # In auto mode, we use LoRA if present (can be enhanced later with complexity detection)
            use_lora = bool(character.loras)
        
        if use_lora and character.loras:
            for lora_info in character.loras:
                # LoRA ID lookup to get trigger words if not provided in JSON
                lora_id = lora_info.get("lora_id")
                weight = lora_info.get("weight", 0.7)
                
                lora_obj = self.db.query(LoRA).filter(LoRA.id == lora_id).first()
                if lora_obj:
                    # Triggers go to Identity layer
                    for trigger in (lora_obj.trigger_words or []):
                        if trigger not in layers[LAYER_IDENTITY]:
                            layers[LAYER_IDENTITY].append(trigger)
                    
                    # LoRA tag
                    layers[LAYER_IDENTITY].append(f"<lora:{lora_obj.name}:{weight}>")

        # 7. Inject Style LoRAs (Atmosphere)
        if style_loras:
            for lora_info in style_loras:
                name = lora_info.get("name")
                weight = lora_info.get("weight", 0.7)
                triggers = lora_info.get("trigger_words", [])
                for trigger in triggers:
                    if trigger not in layers[LAYER_ATMOSPHERE]:
                        layers[LAYER_ATMOSPHERE].append(trigger)
                layers[LAYER_ATMOSPHERE].append(f"<lora:{name}:{weight}>")

        # 8. Add Quality Tags to Layer 0
        if not layers[LAYER_QUALITY]:
            layers[LAYER_QUALITY] = ["masterpiece", "best_quality"]

        return self._flatten_layers(layers, has_character_lora=use_lora)

    def compose(
        self,
        tags: List[str],
        character_loras: Optional[List[Dict]] = None,
        style_loras: Optional[List[Dict]] = None,
    ) -> str:
        """Generic composition without direct DB character object."""
        layers: List[List[str]] = [[] for _ in range(12)]
        tag_info = self.get_tag_info(tags)
        
        for tag in tags:
            norm_tag = tag.lower().replace(" ", "_").strip()
            info = tag_info.get(norm_tag, {"layer": LAYER_SUBJECT})
            layers[info["layer"]].append(tag)
            
        if character_loras:
            for lora in character_loras:
                for trigger in lora.get("trigger_words", []):
                    if trigger not in layers[LAYER_IDENTITY]:
                        layers[LAYER_IDENTITY].append(trigger)
                layers[LAYER_IDENTITY].append(f"<lora:{lora['name']}:{lora.get('weight', 0.7)}>")
                
        if style_loras:
            for lora in style_loras:
                for trigger in lora.get("trigger_words", []):
                    if trigger not in layers[LAYER_ATMOSPHERE]:
                        layers[LAYER_ATMOSPHERE].append(trigger)
                layers[LAYER_ATMOSPHERE].append(f"<lora:{lora['name']}:{lora.get('weight', 0.7)}>")

        if not layers[LAYER_QUALITY]:
            layers[LAYER_QUALITY] = ["masterpiece", "best_quality"]

        return self._flatten_layers(layers, has_character_lora=bool(character_loras))

    def _flatten_layers(self, layers: List[List[str]], has_character_lora: bool = False) -> str:
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

def get_v3_prompt_builder():
    db = SessionLocal()
    try:
        yield V3PromptBuilder(db)
    finally:
        db.close()
