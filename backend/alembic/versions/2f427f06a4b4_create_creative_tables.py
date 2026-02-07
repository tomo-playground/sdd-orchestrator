"""create_creative_tables

Revision ID: 2f427f06a4b4
Revises: fda928418f15
Create Date: 2026-02-07 21:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2f427f06a4b4"
down_revision: Union[str, Sequence[str], None] = "fda928418f15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SYSTEM_PRESETS = [
    {
        "name": "Leader",
        "role_description": "창작 세션을 총괄하는 리더 에이전트. 각 라운드의 결과를 평가하고 최종 방향을 결정합니다.",
        "system_prompt": (
            "당신은 창작 세션의 리더입니다. 에이전트들의 제안을 객관적으로 평가하고, "
            "평가 기준에 따라 최선의 결과물을 선택하세요. "
            "각 라운드마다 명확한 피드백과 개선 방향을 제시합니다."
        ),
        "model_provider": "gemini",
        "model_name": "gemini-2.0-flash",
        "temperature": 0.3,
        "is_system": True,
    },
    {
        "name": "파격형 에이전트",
        "role_description": "관습을 깨는 독창적 아이디어를 생성하는 에이전트. 높은 temperature로 예상치 못한 조합을 시도합니다.",
        "system_prompt": (
            "당신은 파격적인 창작자입니다. 기존 틀을 벗어난 과감한 아이디어를 제시하세요. "
            "뻔한 전개보다 의외성과 신선함을 최우선으로 추구합니다. "
            "다른 에이전트의 피드백을 반영하되, 독창성은 절대 포기하지 마세요."
        ),
        "model_provider": "gemini",
        "model_name": "gemini-2.0-flash",
        "temperature": 1.0,
        "is_system": True,
    },
    {
        "name": "안정형 에이전트",
        "role_description": "구조적 완성도와 논리적 일관성을 중시하는 에이전트. 안정적이고 검증된 패턴을 기반으로 제안합니다.",
        "system_prompt": (
            "당신은 안정적인 창작자입니다. 스토리 구조, 캐릭터 일관성, 논리적 흐름을 최우선으로 고려하세요. "
            "기승전결이 명확하고 독자가 이해하기 쉬운 결과물을 만드세요. "
            "파격보다는 완성도 높은 결과물을 목표로 합니다."
        ),
        "model_provider": "gemini",
        "model_name": "gemini-2.0-flash",
        "temperature": 0.5,
        "is_system": True,
    },
    {
        "name": "감성형 에이전트",
        "role_description": "감정적 공감과 몰입감을 극대화하는 에이전트. 독자의 감정을 자극하는 표현과 분위기를 생성합니다.",
        "system_prompt": (
            "당신은 감성적인 창작자입니다. 독자의 마음을 움직이는 감정 표현에 집중하세요. "
            "캐릭터의 내면 심리, 분위기 묘사, 감정선의 흐름을 섬세하게 다듬으세요. "
            "읽는 사람이 몰입하고 공감할 수 있는 결과물을 만드세요."
        ),
        "model_provider": "gemini",
        "model_name": "gemini-2.0-flash",
        "temperature": 0.9,
        "is_system": True,
    },
]


def upgrade() -> None:
    """Create creative engine tables and seed system presets.

    Uses inspector to check if tables already exist because
    Base.metadata.create_all() may have created them at startup.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # 1. creative_agent_presets
    if "creative_agent_presets" not in existing_tables:
        op.create_table(
            "creative_agent_presets",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(100), unique=True, nullable=False),
            sa.Column("role_description", sa.Text(), nullable=False),
            sa.Column("system_prompt", sa.Text(), nullable=False),
            sa.Column("model_provider", sa.String(20), nullable=False),
            sa.Column("model_name", sa.String(50), nullable=False),
            sa.Column("temperature", sa.Float(), nullable=True),
            sa.Column(
                "is_system",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), onupdate=sa.func.now()),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
        )
        op.create_index(
            "ix_creative_agent_presets_deleted_at",
            "creative_agent_presets",
            ["deleted_at"],
        )

    # 2. creative_sessions
    if "creative_sessions" not in existing_tables:
        op.create_table(
            "creative_sessions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("task_type", sa.String(30), nullable=False),
            sa.Column("objective", sa.Text(), nullable=False),
            sa.Column(
                "evaluation_criteria",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
            ),
            sa.Column(
                "character_id",
                sa.Integer(),
                sa.ForeignKey("characters.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "context",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
            sa.Column(
                "agent_config",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
            sa.Column(
                "final_output",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
            sa.Column("max_rounds", sa.Integer(), nullable=True),
            sa.Column(
                "total_token_usage",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), onupdate=sa.func.now()),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
        )
        op.create_index(
            "ix_creative_sessions_task_type",
            "creative_sessions",
            ["task_type"],
        )
        op.create_index(
            "ix_creative_sessions_deleted_at",
            "creative_sessions",
            ["deleted_at"],
        )

    # 3. creative_session_rounds
    if "creative_session_rounds" not in existing_tables:
        op.create_table(
            "creative_session_rounds",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "session_id",
                sa.Integer(),
                sa.ForeignKey("creative_sessions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("round_number", sa.Integer(), nullable=False),
            sa.Column("leader_summary", sa.Text(), nullable=False),
            sa.Column("round_decision", sa.String(20), nullable=False),
            sa.Column("best_agent_role", sa.String(50), nullable=True),
            sa.Column("best_score", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index(
            "ix_creative_session_rounds_session_id",
            "creative_session_rounds",
            ["session_id"],
        )

    # 4. creative_traces
    if "creative_traces" not in existing_tables:
        op.create_table(
            "creative_traces",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "session_id",
                sa.Integer(),
                sa.ForeignKey("creative_sessions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("round_number", sa.Integer(), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("trace_type", sa.String(20), nullable=False),
            sa.Column("agent_role", sa.String(50), nullable=False),
            sa.Column(
                "agent_preset_id",
                sa.Integer(),
                sa.ForeignKey("creative_agent_presets.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("input_prompt", sa.Text(), nullable=False),
            sa.Column("output_content", sa.Text(), nullable=False),
            sa.Column("score", sa.Float(), nullable=True),
            sa.Column("feedback", sa.Text(), nullable=True),
            sa.Column("model_id", sa.String(100), nullable=False),
            sa.Column(
                "token_usage",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
            sa.Column("latency_ms", sa.Integer(), nullable=False),
            sa.Column("temperature", sa.Float(), nullable=False),
            sa.Column(
                "parent_trace_id",
                sa.Integer(),
                sa.ForeignKey("creative_traces.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("diff_summary", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
        # Composite indexes matching the model's __table_args__
        op.create_index(
            "ix_creative_traces_session_round_seq",
            "creative_traces",
            ["session_id", "round_number", "sequence"],
        )
        op.create_index(
            "ix_creative_traces_session_type",
            "creative_traces",
            ["session_id", "trace_type"],
        )
        op.create_index(
            "ix_creative_traces_session_role",
            "creative_traces",
            ["session_id", "agent_role"],
        )

    # Seed system presets (idempotent: skip if already seeded)
    presets_table = sa.table(
        "creative_agent_presets",
        sa.column("name", sa.String),
        sa.column("role_description", sa.Text),
        sa.column("system_prompt", sa.Text),
        sa.column("model_provider", sa.String),
        sa.column("model_name", sa.String),
        sa.column("temperature", sa.Float),
        sa.column("is_system", sa.Boolean),
    )

    existing_count = conn.execute(
        sa.select(sa.func.count())
        .select_from(presets_table)
        .where(sa.column("is_system").is_(True))
    ).scalar()

    if existing_count == 0:
        op.bulk_insert(presets_table, SYSTEM_PRESETS)


def downgrade() -> None:
    """Drop creative engine tables in reverse dependency order."""
    op.drop_table("creative_traces")
    op.drop_table("creative_session_rounds")
    op.drop_table("creative_sessions")
    op.drop_table("creative_agent_presets")
