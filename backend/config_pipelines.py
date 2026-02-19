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
LANGGRAPH_MAX_REVISIONS = int(os.getenv("LANGGRAPH_MAX_REVISIONS", "3"))

# --- Revise: Scene Expansion (Tier 2) ---
REVISE_EXPANSION_ENABLED = os.getenv("REVISE_EXPANSION_ENABLED", "true").lower() == "true"
REVISE_MAX_EXPANSION_SCENES = int(os.getenv("REVISE_MAX_EXPANSION_SCENES", "5"))
LANGGRAPH_DEFAULT_MODE = os.getenv("LANGGRAPH_DEFAULT_MODE", "quick")
LANGGRAPH_AUTO_REVIEW_THRESHOLD = float(os.getenv("LANGGRAPH_AUTO_REVIEW_THRESHOLD", "0.7"))
LANGGRAPH_NARRATIVE_THRESHOLD = float(os.getenv("LANGGRAPH_NARRATIVE_THRESHOLD", "0.6"))
LANGGRAPH_MAX_DIRECTOR_REVISIONS = int(os.getenv("LANGGRAPH_MAX_DIRECTOR_REVISIONS", "3"))
LANGGRAPH_MAX_CONCEPT_REGEN = int(os.getenv("LANGGRAPH_MAX_CONCEPT_REGEN", "2"))

# --- Director-as-Orchestrator ---
LANGGRAPH_MAX_CHECKPOINT_REVISIONS = int(os.getenv("LANGGRAPH_MAX_CHECKPOINT_REVISIONS", "3"))
LANGGRAPH_CHECKPOINT_THRESHOLD = float(os.getenv("LANGGRAPH_CHECKPOINT_THRESHOLD", "0.7"))
LANGGRAPH_CHECKPOINT_LOW_THRESHOLD = float(os.getenv("LANGGRAPH_CHECKPOINT_LOW_THRESHOLD", "0.4"))
LANGGRAPH_CHECKPOINT_HIGH_THRESHOLD = float(os.getenv("LANGGRAPH_CHECKPOINT_HIGH_THRESHOLD", "0.85"))

# --- Phase 10-A: True Agentic Architecture ---
# Director ReAct Loop
LANGGRAPH_MAX_REACT_STEPS = int(os.getenv("LANGGRAPH_MAX_REACT_STEPS", "3"))

# Review Self-Reflection
LANGGRAPH_REFLECTION_ENABLED = os.getenv("LANGGRAPH_REFLECTION_ENABLED", "true").lower() == "true"

# Writer Planning Step
LANGGRAPH_PLANNING_ENABLED = os.getenv("LANGGRAPH_PLANNING_ENABLED", "true").lower() == "true"

# --- Phase 10-B: Tool-Calling Agent ---
# 노드당 최대 도구 호출 횟수 (비용 가드레일)
MAX_TOOL_CALLS_PER_NODE = int(os.getenv("MAX_TOOL_CALLS_PER_NODE", "5"))

# --- Phase 10-C-3: Critic Debate ---
# 최대 토론 라운드 (비용 가드레일)
MAX_DEBATE_ROUNDS = int(os.getenv("MAX_DEBATE_ROUNDS", "2"))
# 전체 토론 타임아웃 (초)
DEBATE_TIMEOUT_SEC = int(os.getenv("DEBATE_TIMEOUT_SEC", "60"))
# KPI 기반 수렴 판단 임계값
CONVERGENCE_SCORE_THRESHOLD = float(os.getenv("CONVERGENCE_SCORE_THRESHOLD", "0.7"))
CONVERGENCE_HOOK_THRESHOLD = float(os.getenv("CONVERGENCE_HOOK_THRESHOLD", "0.6"))
# Groupthink 감지 유사도 임계값
GROUPTHINK_SIMILARITY_THRESHOLD = float(os.getenv("GROUPTHINK_SIMILARITY_THRESHOLD", "0.85"))

# --- Feedback Presets (Interactive Feedback) ---
FEEDBACK_PRESETS: dict[str, dict] = {
    "hook_boost": {
        "id": "hook_boost",
        "label": "후킹 강화",
        "icon": "zap",
        "feedback": "첫 씬의 Hook을 더 강렬하게 수정. 질문형/충격형/감정형 중 하나로 변경",
    },
    "more_dramatic": {
        "id": "more_dramatic",
        "label": "더 극적으로",
        "icon": "flame",
        "feedback": "전체 감정 곡선의 진폭을 키우고 클라이맥스를 더 강렬하게",
    },
    "tone_change": {
        "id": "tone_change",
        "label": "톤 변경",
        "icon": "mic",
        "feedback": "화자의 톤을 {tone}(으)로 변경. 전체 대사의 어조와 문체를 통일",
        "has_params": True,
        "param_options": {"tone": ["유머러스", "진지한", "감동적", "공포", "냉소적"]},
    },
    "shorten": {
        "id": "shorten",
        "label": "짧게 줄이기",
        "icon": "scissors",
        "feedback": "불필요한 씬을 제거하고 핵심만 남기기",
    },
}

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

# --- Research Node — Quality Scoring ---
RESEARCH_QUALITY_LOW = float(os.getenv("RESEARCH_QUALITY_LOW", "0.3"))
RESEARCH_QUALITY_THRESHOLD = float(os.getenv("RESEARCH_QUALITY_THRESHOLD", "0.5"))

# Research Node — Retry (Tier 2-5)
RESEARCH_MAX_RETRIES = int(os.getenv("RESEARCH_MAX_RETRIES", "1"))

# --- Research Node — Material Analysis ---
RESEARCH_URL_FETCH_TIMEOUT: int = int(os.getenv("RESEARCH_URL_FETCH_TIMEOUT", "15"))
RESEARCH_URL_MAX_BYTES: int = int(os.getenv("RESEARCH_URL_MAX_BYTES", "500000"))
RESEARCH_MAX_REFERENCES: int = int(os.getenv("RESEARCH_MAX_REFERENCES", "5"))

# --- Ollama (Local LLM) Configuration ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
OLLAMA_DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "exaone3.5:7.8b")
