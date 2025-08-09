"""Add meta_json to courses table if missing

Revision ID: c1d2e3f4
Revises: b6d2a1c3e4f5
Create Date: 2025-08-08

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4"
down_revision: Union[str, None] = "b6d2a1c3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "courses" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("courses")}
        if "meta_json" not in cols:
            op.add_column("courses", sa.Column("meta_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "courses" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("courses")}
        if "meta_json" in cols:
            op.drop_column("courses", "meta_json")
