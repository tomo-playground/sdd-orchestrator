"""Cascade casting changes to scene data (character_actions + image_prompt).

When a storyboard's speaker→character mapping changes, this module propagates
the change to scene_character_actions and cleans/swaps LoRA tags in image_prompt.
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from config import logger

_LORA_TAG_RE = re.compile(r"<lora:([^:>]+):([^>]+)>")


def swap_character_in_prompt(
    prompt: str,
    old_loras: list[dict],
    new_loras: list[dict],
) -> str:
    """Replace old character's LoRA tags and trigger words with new character's."""
    if not prompt:
        return prompt

    old_names = {lo.get("name") for lo in old_loras if lo.get("name")}
    old_triggers = set()
    for lo in old_loras:
        old_triggers.update(tw for tw in lo.get("trigger_words", []) if tw)

    if not old_names and not old_triggers:
        # Nothing to remove; just prepend new LoRAs if any
        new_tokens = _build_lora_tokens(new_loras)
        return ", ".join(new_tokens + [prompt]) if new_tokens else prompt

    tokens = [t.strip() for t in prompt.split(",") if t.strip()]
    filtered = []
    lora_insert_pos = 0

    for token in tokens:
        m = _LORA_TAG_RE.match(token)
        if m:
            if m.group(1) in old_names:
                continue  # Drop old character LoRA
            lora_insert_pos = len(filtered) + 1
            filtered.append(token)
            continue

        bare = token.strip().strip("()").split(":")[0].strip()
        if bare in old_triggers:
            continue  # Drop old trigger word

        filtered.append(token)

    new_tokens = _build_lora_tokens(new_loras)
    result = filtered[:lora_insert_pos] + new_tokens + filtered[lora_insert_pos:]
    return ", ".join(result)


def _build_lora_tokens(loras: list[dict]) -> list[str]:
    """Build LoRA tag strings and trigger words from character loras JSONB."""
    tokens: list[str] = []
    for lo in loras:
        lora_type = lo.get("lora_type", "")
        if lora_type == "style":
            continue  # Style LoRAs are managed by StyleProfile
        name = lo.get("name", "")
        weight = lo.get("weight", 0.7)
        if name:
            tokens.append(f"<lora:{name}:{weight}>")
        for tw in lo.get("trigger_words", []) or []:
            if tw:
                tokens.append(tw)
    return tokens


def cascade_casting_to_scenes(
    storyboard_id: int,
    old_map: dict[str, int],
    new_map: dict[str, int],
    db: Session,
) -> int:
    """Propagate casting changes to scenes' character_actions and image_prompt.

    Args:
        storyboard_id: Target storyboard.
        old_map: Previous speaker->character_id mapping.
        new_map: New speaker->character_id mapping.
        db: DB session (caller manages commit).

    Returns:
        Number of scenes updated.
    """
    from models.associations import SceneCharacterAction
    from models.character import Character
    from models.scene import Scene

    changed: dict[str, tuple[int, int]] = {}
    for speaker, new_id in new_map.items():
        old_id = old_map.get(speaker)
        if old_id and old_id != new_id:
            changed[speaker] = (old_id, new_id)

    if not changed:
        return 0

    all_ids = set()
    for old_id, new_id in changed.values():
        all_ids.update((old_id, new_id))
    chars = {c.id: c for c in db.query(Character).filter(Character.id.in_(all_ids)).all()}

    scenes = db.query(Scene).filter(Scene.storyboard_id == storyboard_id, Scene.deleted_at.is_(None)).all()

    updated = 0
    for speaker, (old_id, new_id) in changed.items():
        old_char = chars.get(old_id)
        new_char = chars.get(new_id)
        old_loras = (old_char.loras or []) if old_char else []
        new_loras = (new_char.loras or []) if new_char else []

        matched = [s for s in scenes if s.speaker == speaker]
        if not matched:
            continue

        scene_ids = [s.id for s in matched]

        # 1. Remap scene_character_actions
        rows_updated = (
            db.query(SceneCharacterAction)
            .filter(
                SceneCharacterAction.scene_id.in_(scene_ids),
                SceneCharacterAction.character_id == old_id,
            )
            .update(
                {SceneCharacterAction.character_id: new_id},
                synchronize_session=False,
            )
        )

        # 2. Swap LoRA/trigger in image_prompt
        if old_loras or new_loras:
            for scene in matched:
                if scene.image_prompt:
                    scene.image_prompt = swap_character_in_prompt(
                        scene.image_prompt,
                        old_loras,
                        new_loras,
                    )

        updated += len(matched)
        logger.info(
            "[CastingSync] Speaker %s: char %d->%d, %d scenes, %d actions remapped",
            speaker,
            old_id,
            new_id,
            len(matched),
            rows_updated,
        )

    return updated


def ensure_dialogue_speakers_in_db(
    storyboard_id: int,
    db: Session,
) -> int:
    """Fix speaker alternation for Dialogue storyboards in DB (in-place).

    If all scenes have speaker="A" (common when structure was changed from
    Monologue to Dialogue), alternate non-Narrator scenes as A/B.

    Returns:
        Number of scenes whose speaker was changed.
    """
    from models.scene import Scene

    scenes = (
        db.query(Scene)
        .filter(Scene.storyboard_id == storyboard_id, Scene.deleted_at.is_(None))
        .order_by(Scene.order)
        .all()
    )
    if not scenes:
        return 0

    speakers = {s.speaker for s in scenes}
    if "A" in speakers and "B" in speakers:
        return 0  # Already has both speakers

    non_narrator = [s for s in scenes if s.speaker != "Narrator"]
    if not non_narrator:
        return 0

    changed = 0
    for i, scene in enumerate(non_narrator):
        new_speaker = "A" if i % 2 == 0 else "B"
        if scene.speaker != new_speaker:
            scene.speaker = new_speaker
            changed += 1

    if changed:
        logger.info(
            "[CastingSync] Dialogue speaker alternation fixed: %d/%d scenes",
            changed,
            len(non_narrator),
        )
    return changed
