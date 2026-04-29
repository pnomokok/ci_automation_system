"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-28 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "repositories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("url", sa.String(2048), nullable=False, unique=True),
        sa.Column("default_branch", sa.String(255), nullable=False, server_default="main"),
        sa.Column("webhook_secret", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "pipelines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("repo_id", sa.String(36), sa.ForeignKey("repositories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("repo_url", sa.String(2048), nullable=False),
        sa.Column("branch", sa.String(255), nullable=False),
        sa.Column("commit_hash", sa.String(40), nullable=True),
        sa.Column("commit_msg", sa.String(2048), nullable=True),
        sa.Column("commit_author", sa.String(255), nullable=True),
        sa.Column("trigger_type", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(20), nullable=False, server_default="QUEUED"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_pipelines_status", "pipelines", ["status"])
    op.create_index("ix_pipelines_repo_id", "pipelines", ["repo_id"])
    op.create_index("ix_pipelines_created_at", "pipelines", ["created_at"])

    op.create_table(
        "steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("pipeline_id", sa.String(36), sa.ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(20), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
    )
    op.create_index("ix_steps_pipeline_id", "steps", ["pipeline_id"])

    op.create_table(
        "logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("step_id", sa.String(36), sa.ForeignKey("steps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("stream", sa.String(10), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
    )
    op.create_index("ix_logs_step_id", "logs", ["step_id"])


def downgrade() -> None:
    op.drop_table("logs")
    op.drop_table("steps")
    op.drop_table("pipelines")
    op.drop_table("repositories")
    op.drop_table("users")
