"""Character management package — public API.

Usage:
    from services.characters import create_character, list_characters, ConflictError
"""

from .action_resolver import (
    auto_populate_character_actions,
    extract_actions_from_context_tags,
)
from .crud import (
    ConflictError,
    create_character,
    get_character_or_raise,
    list_characters,
    list_trashed_characters,
    permanently_delete_character,
    restore_character,
    soft_delete_character,
    update_character,
)
from .lora_enrichment import enrich_character_loras
from .preview import (
    assign_wizard_preview,
    batch_regenerate_references,
    edit_preview,
    enhance_preview,
    generate_wizard_preview,
    regenerate_reference,
)
from .speaker_resolver import (
    assign_speakers,
    resolve_all_speakers,
    resolve_speaker_to_character,
)

__all__ = [
    # crud
    "ConflictError",
    "create_character",
    "get_character_or_raise",
    "list_characters",
    "list_trashed_characters",
    "permanently_delete_character",
    "restore_character",
    "soft_delete_character",
    "update_character",
    # lora
    "enrich_character_loras",
    # preview
    "assign_wizard_preview",
    "batch_regenerate_references",
    "edit_preview",
    "enhance_preview",
    "generate_wizard_preview",
    "regenerate_reference",
    # action_resolver
    "auto_populate_character_actions",
    "extract_actions_from_context_tags",
    # speaker_resolver
    "assign_speakers",
    "resolve_all_speakers",
    "resolve_speaker_to_character",
]
