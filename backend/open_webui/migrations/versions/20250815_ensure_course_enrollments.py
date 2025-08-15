"""Ensure course_enrollments table exists

Revision ID: 20250815_ensure_course_enrollments
Revises: merge_c1d2e3f4_zzdrop
Create Date: 2025-08-15 00:00:00

This migration is idempotent: it will create the legacy `course_enrollments`
table if it is missing (useful for deployments where a prior cleanup removed
the table but the running code still expects it).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from open_webui.migrations.util import get_existing_tables

# revision identifiers, used by Alembic.
revision: str = "20250815_ensure_course_enrollments"
down_revision: Union[str, Sequence[str], None] = "merge_c1d2e3f4_zzdrop"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op: migration intentionally disabled to prevent re-creating legacy course_enrollments table."""
    return


def downgrade() -> None:
    """No-op downgrade for enrollment migration (table already removed)."""
    return
