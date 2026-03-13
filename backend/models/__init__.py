"""SQLAlchemy models for Shorts Producer."""

from models.activity_log import ActivityLog
from models.associations import CharacterTag, SceneCharacterAction, SceneTag
from models.background import Background
from models.base import Base
from models.character import Character
from models.creative import (
    CreativeAgentPreset,
    CreativeSession,
    CreativeSessionRound,
    CreativeTrace,
)
from models.group import Group
from models.lab import LabExperiment
from models.lora import LoRA
from models.media_asset import MediaAsset
from models.music_preset import MusicPreset
from models.project import Project
from models.render_history import RenderHistory
from models.render_preset import RenderPreset
from models.scene import Scene
from models.scene_quality import SceneQualityScore
from models.sd_model import Embedding, SDModel, StyleProfile
from models.storyboard import Storyboard
from models.storyboard_character import StoryboardCharacter
from models.tag import ClassificationRule, Tag, TagEffectiveness, TagRule
from models.tag_alias import TagAlias
from models.tag_filter import TagFilter
from models.voice_preset import VoicePreset
from models.youtube_credential import YouTubeCredential

__all__ = [
    "Background",
    "Base",
    "Tag",
    "TagEffectiveness",
    "TagRule",
    "ClassificationRule",
    "TagFilter",
    "TagAlias",
    "Character",
    "CharacterTag",
    "LoRA",
    "SDModel",
    "Embedding",
    "StyleProfile",
    "Project",
    "Group",
    "RenderPreset",
    "Storyboard",
    "Scene",
    "MediaAsset",
    "SceneTag",
    "SceneCharacterAction",
    "ActivityLog",
    "SceneQualityScore",
    "RenderHistory",
    "VoicePreset",
    "MusicPreset",
    "StoryboardCharacter",
    "YouTubeCredential",
    "LabExperiment",
    "CreativeAgentPreset",
    "CreativeSession",
    "CreativeSessionRound",
    "CreativeTrace",
]
