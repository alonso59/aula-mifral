"""Add Study & Learn preset fields

Revision ID: a4a_study_learn
Revises: e4c7a8b0f9d1
Create Date: 2025-08-08 01:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
# Use a short, filename-matching revision id for merge compatibility
revision = "a4a"
down_revision = "e4c7a8b0f9d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "course_presets" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("course_presets")}
        if "name" not in cols:
            op.add_column("course_presets", sa.Column("name", sa.String(), nullable=True))
        if "is_default" not in cols:
            op.add_column(
                "course_presets",
                sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            )
        if "retrieval_json" not in cols:
            op.add_column("course_presets", sa.Column("retrieval_json", sa.JSON(), nullable=True))
        if "safety_json" not in cols:
            op.add_column("course_presets", sa.Column("safety_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "course_presets" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("course_presets")}
        if "safety_json" in cols:
            op.drop_column("course_presets", "safety_json")
        bind = op.get_bind(); insp = sa.inspect(bind); cols = {c["name"] for c in insp.get_columns("course_presets")}
        if "retrieval_json" in cols:
            op.drop_column("course_presets", "retrieval_json")
        bind = op.get_bind(); insp = sa.inspect(bind); cols = {c["name"] for c in insp.get_columns("course_presets")}
        if "is_default" in cols:
            op.drop_column("course_presets", "is_default")
        bind = op.get_bind(); insp = sa.inspect(bind); cols = {c["name"] for c in insp.get_columns("course_presets")}
        if "name" in cols:
            op.drop_column("course_presets", "name")
