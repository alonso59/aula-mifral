"""Merge heads for classroom feature

Revision ID: b6d2a1c3e4f5
Revises: a4a, f1f0a0a1b2c3
Create Date: 2025-08-08

This is a no-op merge to resolve multiple heads created by
parallel classroom Phase 1/4A migrations.
"""

from typing import Sequence, Union

# Alembic imports kept for consistency with other revisions
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


# revision identifiers, used by Alembic.
revision = "b6d2a1c3e4f5"
down_revision = ("a4a", "f1f0a0a1b2c3")
branch_labels = None
depends_on = None


def upgrade() -> None:
	# No-op merge
	pass


def downgrade() -> None:
	# No-op split
	pass

