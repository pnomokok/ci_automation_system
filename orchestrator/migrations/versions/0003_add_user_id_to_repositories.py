"""add user_id to repositories for ownership tracking

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-08 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("repositories", sa.Column(
        "user_id", sa.String(36),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    ))
    op.create_index("ix_repositories_user_id", "repositories", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_repositories_user_id", "repositories")
    op.drop_column("repositories", "user_id")
