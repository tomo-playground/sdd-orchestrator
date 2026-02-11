"""LoRA metadata denormalization for character responses.

Trade-off: We denormalize LoRA name/trigger_words/lora_type into the character's
JSONB `loras` field to avoid N+1 queries on every read. This means LoRA renames
require re-enrichment, but reads are fast and self-contained.
"""

from sqlalchemy.orm import Session

from models import LoRA


def enrich_character_loras(db: Session, loras: list[dict]) -> list[dict]:
    """Batch-query LoRA table and merge name/trigger_words/lora_type into each entry.

    Used by create/update endpoints where a pre-fetched lora_map is not available.
    """
    if not loras:
        return loras

    lora_ids = [item.get("lora_id") for item in loras if item.get("lora_id")]
    if not lora_ids:
        return loras

    lora_objs = db.query(LoRA).filter(LoRA.id.in_(lora_ids)).all()
    lora_map = {obj.id: obj for obj in lora_objs}
    return enrich_with_lora_map(loras, lora_map)


def enrich_with_lora_map(loras: list[dict], lora_map: dict[int, LoRA]) -> list[dict]:
    """Enrich LoRA entries using a pre-fetched lora_map (avoids redundant queries).

    Used by list_characters where all LoRAs are pre-fetched once.
    """
    enriched = []
    for item in loras:
        entry = item.copy()
        lid = entry.get("lora_id")
        if lid and lid in lora_map:
            lora = lora_map[lid]
            entry["name"] = lora.name
            entry["trigger_words"] = lora.trigger_words
            entry["lora_type"] = lora.lora_type
        enriched.append(entry)
    return enriched
