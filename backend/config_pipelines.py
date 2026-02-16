"""Pipeline & integration constants extracted from config.py.

YouTube, Lab, Creative Engine, LangGraph, Ollama 설정을 분리하여
config.py 파일 크기를 400줄 이하로 유지한다.
"""

from __future__ import annotations

import os

# --- YouTube Upload Configuration ---
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")
YOUTUBE_REDIRECT_URI = os.getenv("YOUTUBE_REDIRECT_URI", "http://localhost:3000/manage?tab=youtube")
YOUTUBE_TOKEN_ENCRYPTION_KEY = os.getenv("YOUTUBE_TOKEN_ENCRYPTION_KEY", "")
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]
YOUTUBE_API_QUOTA_DAILY = int(os.getenv("YOUTUBE_API_QUOTA_DAILY", "10000"))
YOUTUBE_UPLOAD_COST = int(os.getenv("YOUTUBE_UPLOAD_COST", "1600"))

# --- Lab Configuration ---
LAB_DEFAULT_SD_STEPS = int(os.getenv("LAB_DEFAULT_SD_STEPS", "20"))
LAB_BATCH_MAX_SIZE = int(os.getenv("LAB_BATCH_MAX_SIZE", "20"))

# --- Creative Engine Configuration ---
CREATIVE_MAX_ROUNDS = int(os.getenv("CREATIVE_MAX_ROUNDS", "3"))
CREATIVE_LEADER_MODEL = os.getenv("CREATIVE_LEADER_MODEL", "gemini-2.5-flash")
CREATIVE_PIPELINE_MAX_RETRIES = int(os.getenv("CREATIVE_PIPELINE_MAX_RETRIES", "2"))

# Creative Lab: Agent Categories (SSOT for Frontend)
CREATIVE_AGENT_CATEGORIES = [
    {"value": "concept", "label": "Concept"},
    {"value": "production", "label": "Production"},
]

# Creative Lab: Agent-Template Mapping
CREATIVE_AGENT_TEMPLATES: dict[str, str] = {
    # Concept Phase
    "emotional_arc": "creative/concept_architect.j2",
    "visual_hook": "creative/concept_architect.j2",
    "narrative_twist": "creative/concept_architect.j2",
    "devils_advocate": "creative/devils_advocate.j2",
    "creative_director": "creative/director_evaluate.j2",
    "reference_analyst": "creative/reference_analyst.j2",
    "material_analyst": "creative/material_analyst.j2",
    # Production Phase
    "scriptwriter": "creative/scriptwriter.j2",
    "cinematographer": "creative/cinematographer.j2",
    "tts_designer": "creative/tts_designer.j2",
    "sound_designer": "creative/sound_designer.j2",
    "copyright_reviewer": "creative/copyright_reviewer.j2",
    # QC Agents
    "script_qc": "creative/script_qc.j2",
}

# --- LangFuse Observability ---
LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL", "http://localhost:3001")

# --- LangGraph ---
LANGGRAPH_MAX_REVISIONS = int(os.getenv("LANGGRAPH_MAX_REVISIONS", "2"))
LANGGRAPH_DEFAULT_MODE = os.getenv("LANGGRAPH_DEFAULT_MODE", "quick")
LANGGRAPH_AUTO_REVIEW_THRESHOLD = float(os.getenv("LANGGRAPH_AUTO_REVIEW_THRESHOLD", "0.7"))
LANGGRAPH_MAX_DIRECTOR_REVISIONS = int(os.getenv("LANGGRAPH_MAX_DIRECTOR_REVISIONS", "1"))

LANGGRAPH_PRESETS: dict[str, dict] = {
    "quick": {
        "id": "quick",
        "name": "Quick",
        "name_ko": "빠른 생성",
        "description": "Gemini 1회 호출로 빠르게 대본 생성",
        "mode": "quick",
    },
    "full_auto": {
        "id": "full_auto",
        "name": "Full Auto",
        "name_ko": "풀 오토",
        "description": "AI가 컨셉~대본 자동 생성, 검토 후 승인",
        "mode": "full",
        "auto_approve": True,
    },
    "creator": {
        "id": "creator",
        "name": "Creator",
        "name_ko": "크리에이터",
        "description": "AI 초안 생성 + 핵심 결정은 사용자",
        "mode": "full",
        "auto_approve": False,
    },
}

# --- Ollama (Local LLM) Configuration ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
OLLAMA_DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "exaone3.5:7.8b")
