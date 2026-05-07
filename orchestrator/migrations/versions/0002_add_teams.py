"""add teams and team_members; add team_id to pipelines and repositories

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-06 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "team_members",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("team_id", sa.String(36), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("team_id", "user_id"),
    )
    op.create_index("ix_team_members_user_id", "team_members", ["user_id"])
    op.create_index("ix_team_members_team_id", "team_members", ["team_id"])

    op.add_column("pipelines", sa.Column(
        "team_id", sa.String(36),
        sa.ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    ))
    op.create_index("ix_pipelines_team_id", "pipelines", ["team_id"])

    op.add_column("repositories", sa.Column(
        "team_id", sa.String(36),
        sa.ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    ))
    op.create_index("ix_repositories_team_id", "repositories", ["team_id"])


def downgrade() -> None:
    op.drop_index("ix_repositories_team_id", "repositories")
    op.drop_column("repositories", "team_id")
    op.drop_index("ix_pipelines_team_id", "pipelines")
    op.drop_column("pipelines", "team_id")
    op.drop_index("ix_team_members_user_id", "team_members")
    op.drop_index("ix_team_members_team_id", "team_members")
    op.drop_table("team_members")
    op.drop_table("teams")
