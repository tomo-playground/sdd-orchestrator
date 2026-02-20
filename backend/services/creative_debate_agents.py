"""Creative Lab V2 — Debate agent runners and context.

Contains the 3 Architect, Devil's Advocate, and Director Evaluate async runners.
Extracted from creative_shorts.py for file size compliance.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from jinja2 import Environment, FileSystemLoader

from config import BASE_DIR, CREATIVE_AGENT_TEMPLATES, CREATIVE_LEADER_MODEL, logger
from models.creative import CreativeSession
from services.creative_agents import generate_parallel, get_provider
from services.creative_utils import get_next_sequence, load_preset, parse_json_response, record_trace_sync

_template_env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates")))

# ── Constants ──────────────────────────────────────────────────

ARCHITECT_PERSPECTIVES = [
    {
        "role": "emotional_arc",
        "perspective": "Emotional Arc (감정 곡선과 캐릭터 성장)",
        "focus_instruction": "emotional journey, character growth, and empathy. Make the viewer feel something.",
        "weights": {"hook": 0.2, "arc": 0.4, "feasibility": 0.2, "originality": 0.2},
    },
    {
        "role": "visual_hook",
        "perspective": "Visual Hook (시각적 임팩트와 첫 3초 훅)",
        "focus_instruction": "visual impact and the first 3-second hook. One powerful image drives the entire video.",
        "weights": {"hook": 0.4, "arc": 0.2, "feasibility": 0.2, "originality": 0.2},
    },
    {
        "role": "narrative_twist",
        "perspective": "Narrative Twist (구조적 참신함과 반전)",
        "focus_instruction": "structural novelty and plot twists. Defy expectations to captivate the viewer.",
        "weights": {"hook": 0.2, "arc": 0.2, "feasibility": 0.2, "originality": 0.4},
    },
]


@dataclass
class DebateContext:
    """Grouped parameters for debate round execution."""

    topic: str
    duration: int
    structure: str
    language: str
    max_rounds: int
    character_name: str | None = None
    reference_guidelines: str | None = None
    research_brief: dict | None = None
    prev_concepts: dict | None = None
    director_feedback: str | None = None
    critic_feedback: dict | None = None
    prev_evaluation_str: str | None = None
    director_plan: dict | None = None
    all_round_concepts: list = field(default_factory=list)
    last_eval: dict = field(default_factory=dict)


# ── Agent runners ──────────────────────────────────────────────


async def run_reference_analyst(db, session: CreativeSession, ctx: DebateContext) -> dict | None:
    """Phase 0: Analyze user-provided references."""
    template = _template_env.get_template(CREATIVE_AGENT_TEMPLATES["reference_analyst"])
    session_ctx = dict(session.context or {})
    references = session_ctx.get("references", [])
    if not references:
        return None

    prompt = template.render(
        references=references,
        duration=ctx.duration,
        structure=ctx.structure,
        language=ctx.language,
    )

    preset = load_preset(db, "reference_analyst")
    sys_prompt = (
        preset.system_prompt
        if preset
        else "You are a Reference Analyst. Analyze content patterns. Respond only in valid JSON."
    )
    temp = preset.temperature if preset else 0.5

    provider = get_provider("gemini", CREATIVE_LEADER_MODEL)
    start = time.monotonic()
    try:
        result = await provider.generate(
            prompt=prompt,
            system_prompt=sys_prompt,
            temperature=temp,
        )
    except Exception as e:
        logger.warning("[Shorts] Reference Analyst failed: %s", e)
        return None
    elapsed_ms = int((time.monotonic() - start) * 1000)

    seq = get_next_sequence(db, session.id)
    record_trace_sync(
        db,
        session_id=session.id,
        round_number=0,
        sequence=seq,
        trace_type="generation",
        agent_role="reference_analyst",
        agent_preset_id=preset.id if preset else None,
        input_prompt=prompt,
        output_content=result["content"],
        model_id=result["model_id"],
        token_usage=result["token_usage"],
        latency_ms=elapsed_ms,
        temperature=temp,
        phase="reference",
        step_name="reference_analyst",
    )

    try:
        return parse_json_response(result["content"])
    except (json.JSONDecodeError, KeyError):
        logger.warning("[Shorts] Reference Analyst JSON parse failed")
        return None


async def run_architects(db, session: CreativeSession, round_number: int, ctx: DebateContext) -> list[dict]:
    """Run 3 architects in parallel and record traces."""
    template = _template_env.get_template(CREATIVE_AGENT_TEMPLATES["emotional_arc"])
    agents = []

    for arch in ARCHITECT_PERSPECTIVES:
        prev_concept = None
        arch_critic = None
        if ctx.prev_concepts and arch["role"] in ctx.prev_concepts:
            prev_concept = ctx.prev_concepts[arch["role"]]
        if ctx.critic_feedback and arch["role"] in (ctx.critic_feedback.get("by_role") or {}):
            arch_critic = ctx.critic_feedback["by_role"][arch["role"]]

        preset = load_preset(db, arch["role"])
        meta = (preset.agent_metadata or {}) if preset else {}
        perspective = meta.get("perspective", arch["perspective"])
        focus = meta.get("focus_instruction", arch["focus_instruction"])

        prompt = template.render(
            perspective=perspective,
            duration=ctx.duration,
            topic=ctx.topic,
            language=ctx.language,
            structure=ctx.structure,
            character_name=ctx.character_name,
            reference_guidelines=ctx.reference_guidelines,
            research_brief=ctx.research_brief,
            director_plan=ctx.director_plan,
            prev_concept=json.dumps(prev_concept, ensure_ascii=False) if prev_concept else None,
            director_feedback=ctx.director_feedback,
            critic_feedback=arch_critic,
            focus_instruction=focus,
        )

        sys_prompt = (
            preset.system_prompt
            if preset
            else f"You are a Story Architect ({arch['perspective']}). Respond only in valid JSON."
        )
        temp = preset.temperature if preset else 0.9

        agents.append(
            {
                "role": arch["role"],
                "preset_id": preset.id if preset else None,
                "provider": "gemini",
                "model_name": CREATIVE_LEADER_MODEL,
                "system_prompt": sys_prompt,
                "temperature": temp,
                "objective": prompt,
            }
        )

    gen_results = await generate_parallel(agents=agents, objective="")

    for result in gen_results:
        seq = get_next_sequence(db, session.id)
        record_trace_sync(
            db,
            session_id=session.id,
            round_number=round_number,
            sequence=seq,
            trace_type="generation",
            agent_role=result.get("agent_role", "unknown"),
            agent_preset_id=result.get("preset_id"),
            input_prompt=result.get("_prompt", ""),
            output_content=result.get("content", ""),
            model_id=result.get("model_id", "unknown"),
            token_usage=result.get("token_usage", {}),
            latency_ms=result.get("latency_ms", 0),
            temperature=result.get("temperature", 0.9),
            phase="concept",
        )

    return gen_results


async def run_devils_advocate(
    db,
    session: CreativeSession,
    round_number: int,
    concepts: list[dict],
    ctx: DebateContext,
) -> dict | None:
    """Run Devil's Advocate critique on all concepts."""
    template = _template_env.get_template(CREATIVE_AGENT_TEMPLATES["devils_advocate"])
    prompt = template.render(
        concepts=concepts,
        concept_count=len(concepts),
        topic=ctx.topic,
        duration=ctx.duration,
        structure=ctx.structure,
    )

    preset = load_preset(db, "devils_advocate")
    sys_prompt = (
        preset.system_prompt
        if preset
        else "You are a Devil's Advocate. Criticize sharply but constructively. Respond only in valid JSON."
    )
    temp = preset.temperature if preset else 0.7

    provider = get_provider("gemini", CREATIVE_LEADER_MODEL)
    start = time.monotonic()
    try:
        result = await provider.generate(
            prompt=prompt,
            system_prompt=sys_prompt,
            temperature=temp,
        )
    except Exception as e:
        logger.warning("[Shorts] Devil's Advocate failed: %s", e)
        return None
    elapsed_ms = int((time.monotonic() - start) * 1000)

    seq = get_next_sequence(db, session.id)
    record_trace_sync(
        db,
        session_id=session.id,
        round_number=round_number,
        sequence=seq,
        trace_type="generation",
        agent_role="devils_advocate",
        agent_preset_id=preset.id if preset else None,
        input_prompt=prompt,
        output_content=result["content"],
        model_id=result["model_id"],
        token_usage=result["token_usage"],
        latency_ms=elapsed_ms,
        temperature=temp,
        phase="concept",
        step_name="critic",
    )

    try:
        return parse_json_response(result["content"])
    except (json.JSONDecodeError, KeyError):
        logger.warning("[Shorts] Devil's Advocate JSON parse failed")
        return None


async def run_director_evaluate(
    db,
    session: CreativeSession,
    round_number: int,
    concepts: list[dict],
    ctx: DebateContext,
) -> dict:
    """Director evaluates all concepts."""
    template = _template_env.get_template(CREATIVE_AGENT_TEMPLATES["creative_director"])
    prompt = template.render(
        concepts=concepts,
        topic=ctx.topic,
        duration=ctx.duration,
        round_number=round_number,
        max_rounds=ctx.max_rounds,
        critic_analysis=ctx.prev_evaluation_str,
        prev_evaluation=ctx.prev_evaluation_str,
        hook_weight=0.25,
        arc_weight=0.30,
        feasibility_weight=0.25,
        originality_weight=0.20,
    )

    preset = load_preset(db, "creative_director")
    sys_prompt = (
        preset.system_prompt
        if preset
        else "You are a Creative Director. Evaluate concepts strictly. Respond only in valid JSON."
    )
    temp = preset.temperature if preset else 0.3

    provider = get_provider("gemini", CREATIVE_LEADER_MODEL)
    start = time.monotonic()
    result = await provider.generate(
        prompt=prompt,
        system_prompt=sys_prompt,
        temperature=temp,
    )
    elapsed_ms = int((time.monotonic() - start) * 1000)

    seq = get_next_sequence(db, session.id)
    record_trace_sync(
        db,
        session_id=session.id,
        round_number=round_number,
        sequence=seq,
        trace_type="evaluation",
        agent_role="creative_director",
        agent_preset_id=preset.id if preset else None,
        input_prompt=prompt,
        output_content=result["content"],
        model_id=result["model_id"],
        token_usage=result["token_usage"],
        latency_ms=elapsed_ms,
        temperature=temp,
        phase="concept",
    )

    try:
        return parse_json_response(result["content"])
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("[Shorts] Director evaluation parse failed: %s", e)
        roles = [c.get("agent_role", "unknown") for c in concepts]
        return {
            "summary": "Auto-evaluation fallback",
            "decision": "continue",
            "scores": {r: {"score": 0.5, "feedback": "Parse error fallback"} for r in roles},
            "best_agent_role": roles[0] if roles else None,
            "best_score": 0.5,
            "direction": "",
        }
