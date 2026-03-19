"""Add V2 agent preset columns and seed data.

Revision ID: 2a131f2aaf2c
Revises: 3e30b3b1d7cc
Create Date: 2026-02-10

Adds agent_role, category, agent_metadata columns to creative_agent_presets.
Seeds 10 V2 pipeline agent presets and updates existing V1 presets.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "2a131f2aaf2c"
down_revision = "3e30b3b1d7cc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("creative_agent_presets", sa.Column("agent_role", sa.String(50), nullable=True))
    op.add_column("creative_agent_presets", sa.Column("category", sa.String(30), nullable=True))
    op.add_column("creative_agent_presets", sa.Column("agent_metadata", postgresql.JSONB, nullable=True))
    op.create_index(
        "ix_cap_agent_role",
        "creative_agent_presets",
        ["agent_role"],
        unique=True,
        postgresql_where=sa.text("agent_role IS NOT NULL"),
    )

    # Tag existing V1 presets
    op.execute(
        "UPDATE creative_agent_presets SET category = 'v1_debate' WHERE agent_role IS NULL AND deleted_at IS NULL"
    )

    # Seed V2 presets (idempotent: skip if agent_role already exists)
    op.execute("""
        INSERT INTO creative_agent_presets
            (name, role_description, system_prompt, model_provider, model_name,
             temperature, is_system, agent_role, category, agent_metadata)
        VALUES
            ('Reference Analyst',
             'Analyzes user-provided references to extract content patterns and guidelines.',
             'You are a Reference Analyst. Analyze content patterns. Respond only in valid JSON.',
             'gemini', 'gemini-2.0-flash', 0.5, true,
             'reference_analyst', 'v2_concept', NULL),

            ('Emotional Arc Architect',
             'Story Architect focusing on emotional journey, character growth, and empathy.',
             'You are a Story Architect (Emotional Arc). Respond only in valid JSON.',
             'gemini', 'gemini-2.0-flash', 0.9, true,
             'emotional_arc', 'v2_concept',
             '{"perspective": "Emotional Arc (감정 곡선과 캐릭터 성장)", "focus_instruction": "emotional journey, character growth, and empathy. Make the viewer feel something.", "weights": {"hook": 0.2, "arc": 0.4, "feasibility": 0.2, "originality": 0.2}}'),

            ('Visual Hook Architect',
             'Story Architect focusing on visual impact and the first 3-second hook.',
             'You are a Story Architect (Visual Hook). Respond only in valid JSON.',
             'gemini', 'gemini-2.0-flash', 0.9, true,
             'visual_hook', 'v2_concept',
             '{"perspective": "Visual Hook (시각적 임팩트와 첫 3초 훅)", "focus_instruction": "visual impact and the first 3-second hook. One powerful image drives the entire video.", "weights": {"hook": 0.4, "arc": 0.2, "feasibility": 0.2, "originality": 0.2}}'),

            ('Narrative Twist Architect',
             'Story Architect focusing on structural novelty and plot twists.',
             'You are a Story Architect (Narrative Twist). Respond only in valid JSON.',
             'gemini', 'gemini-2.0-flash', 0.9, true,
             'narrative_twist', 'v2_concept',
             '{"perspective": "Narrative Twist (구조적 참신함과 반전)", "focus_instruction": "structural novelty and plot twists. Defy expectations to captivate the viewer.", "weights": {"hook": 0.2, "arc": 0.2, "feasibility": 0.2, "originality": 0.4}}'),

            ('Devil''s Advocate',
             'Criticizes concepts sharply but constructively to improve quality.',
             'You are a Devil''s Advocate. Criticize sharply but constructively. Respond only in valid JSON.',
             'gemini', 'gemini-2.0-flash', 0.7, true,
             'devils_advocate', 'v2_concept', NULL),

            ('Creative Director',
             'Evaluates and scores concepts, makes strategic decisions.',
             'You are a Creative Director. Evaluate concepts strictly. Respond only in valid JSON.',
             'gemini', 'gemini-2.0-flash', 0.3, true,
             'creative_director', 'v2_concept', NULL),

            ('Scriptwriter',
             'Expert scriptwriter for short-form video with 2-pass process.',
             'You are an expert scriptwriter for short-form video. Follow the 2-pass process strictly.',
             'gemini', 'gemini-2.0-flash', 0.8, true,
             'scriptwriter', 'v2_production', NULL),

            ('Cinematographer',
             'Designs AI-generated visuals using Danbooru tags.',
             'You are a cinematographer designing AI-generated visuals. Use only Danbooru tags.',
             'gemini', 'gemini-2.0-flash', 0.8, true,
             'cinematographer', 'v2_production', NULL),

            ('Sound Designer',
             'Recommends BGM direction and sound design for short-form video.',
             'You are a Sound Designer. Recommend BGM direction. Respond in valid JSON only.',
             'gemini', 'gemini-2.0-flash', 0.8, true,
             'sound_designer', 'v2_production', NULL),

            ('Copyright Reviewer',
             'Checks for originality and copyright issues in generated content.',
             'You are a Copyright Reviewer. Check for originality issues. Respond only in valid JSON.',
             'gemini', 'gemini-2.0-flash', 0.8, true,
             'copyright_reviewer', 'v2_production', NULL)
        ON CONFLICT (name) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_index("ix_cap_agent_role", table_name="creative_agent_presets")
    op.drop_column("creative_agent_presets", "agent_metadata")
    op.drop_column("creative_agent_presets", "category")
    op.drop_column("creative_agent_presets", "agent_role")
