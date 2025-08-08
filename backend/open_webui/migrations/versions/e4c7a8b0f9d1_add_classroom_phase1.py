"""Add Virtual Classroom Phase 1 tables (gated by CLASSROOM_MODE)

Revision ID: e4c7a8b0f9d1
Revises: d31026856c01
Create Date: 2025-08-08 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from open_webui.migrations.util import get_existing_tables

# revision identifiers, used by Alembic.
revision: str = "e4c7a8b0f9d1"
down_revision: Union[str, None] = "d31026856c01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_tables = set(get_existing_tables())

    if "courses" not in existing_tables:
        op.create_table(
            "courses",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="draft"),
            sa.Column("created_by", sa.String(), nullable=False),  # user id
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=True),
        )

    if "course_enrollments" not in existing_tables:
        op.create_table(
            "course_enrollments",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("course_id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("is_teacher", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
        )

    if "course_presets" not in existing_tables:
        op.create_table(
            "course_presets",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("course_id", sa.String(), nullable=False),
            sa.Column("provider", sa.String(), nullable=True),
            sa.Column("model_id", sa.String(), nullable=True),
            sa.Column("temperature", sa.Float(), nullable=True),
            sa.Column("max_tokens", sa.Integer(), nullable=True),
            sa.Column("system_prompt_md", sa.Text(), nullable=True),
            sa.Column("tools_json", sa.JSON(), nullable=True),
            sa.Column("knowledge_id", sa.Text(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=True),
        )

    if "materials" not in existing_tables:
        op.create_table(
            "materials",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("course_id", sa.String(), nullable=False),
            sa.Column("kind", sa.String(), nullable=False),  # doc, link, video
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("uri_or_blob_id", sa.Text(), nullable=True),
            sa.Column("meta_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
        )

    if "assignments" not in existing_tables:
        op.create_table(
            "assignments",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("course_id", sa.String(), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("body_md", sa.Text(), nullable=True),
            sa.Column("due_at", sa.BigInteger(), nullable=True),
            sa.Column("attachments_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
        )

    if "submissions" not in existing_tables:
        op.create_table(
            "submissions",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("assignment_id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("text", sa.Text(), nullable=True),
            sa.Column("files_json", sa.JSON(), nullable=True),
            sa.Column("submitted_at", sa.BigInteger(), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default="submitted"),
            sa.Column("grade_json", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    # Drop tables in reverse order to avoid dependency issues
    existing_tables = set(get_existing_tables())
    if "submissions" in existing_tables:
        op.drop_table("submissions")
    existing_tables = set(get_existing_tables())
    if "assignments" in existing_tables:
        op.drop_table("assignments")
    existing_tables = set(get_existing_tables())
    if "materials" in existing_tables:
        op.drop_table("materials")
    existing_tables = set(get_existing_tables())
    if "course_presets" in existing_tables:
        op.drop_table("course_presets")
    existing_tables = set(get_existing_tables())
    if "course_enrollments" in existing_tables:
        op.drop_table("course_enrollments")
    existing_tables = set(get_existing_tables())
    if "courses" in existing_tables:
        op.drop_table("courses")
