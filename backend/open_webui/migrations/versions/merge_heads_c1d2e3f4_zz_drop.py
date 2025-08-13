"""Merge migration to resolve multiple heads

Revision ID: merge_c1d2e3f4_zzdrop
Revises: c1d2e3f4, zz_drop_course_enrollments_20250813
Create Date: 2025-08-13 15:13:17.000000

This is a no-op "merge" migration that unifies two heads so Alembic's
single-head upgrade behavior works on first-run deployments.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "merge_c1d2e3f4_zzdrop"
down_revision: Union[str, Sequence[str], None] = ("c1d2e3f4", "zz_drop_course_enrollments_20250813")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Merge revision: intentionally empty (no schema changes).
    # Its purpose is to mark a single linear head so `alembic upgrade head`
    # works on fresh databases.
    pass


def downgrade():
    # Downgrade isn't meaningful for this merge marker; keep as no-op.
    pass
