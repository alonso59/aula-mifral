"""Drop legacy course_enrollments table (cleanup)

Revision ID: zz_drop_course_enrollments_20250813
Revises: e4c7a8b0f9d1
Create Date: 2025-08-13 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from open_webui.migrations.util import get_existing_tables

# revision identifiers, used by Alembic.
revision: str = "zz_drop_course_enrollments_20250813"
down_revision: Union[str, None] = "e4c7a8b0f9d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Drop the legacy course_enrollments table if it exists.
    This is part of removing the legacy enrollment feature.
    """
    existing_tables = set(get_existing_tables())
    if "course_enrollments" in existing_tables:
        op.drop_table("course_enrollments")


def downgrade() -> None:
    """
    Recreate the course_enrollments table (rollback).
    This recreates the original table schema used before removal.
    """
    existing_tables = set(get_existing_tables())
    if "course_enrollments" not in existing_tables:
        op.create_table(
            "course_enrollments",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("course_id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("is_teacher", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
        )
