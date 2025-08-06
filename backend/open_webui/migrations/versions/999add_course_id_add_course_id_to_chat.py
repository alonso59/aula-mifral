"""Add course_id to chat table

Revision ID: 999add_course_id
Revises: d31026856c01
Create Date: 2025-08-05 20:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "999add_course_id"
down_revision = "d31026856c01"
branch_labels = None
depends_on = None


def upgrade():
    # Add 'course_id' column to the 'chat' table (check if column doesn't already exist)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = inspector.get_columns("chat")
    column_names = [col["name"] for col in columns]
    
    if "course_id" not in column_names:
        op.add_column(
            "chat",
            sa.Column("course_id", sa.Text(), nullable=True),
        )


def downgrade():
    # Remove 'course_id' column from the 'chat' table (check if column exists first)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    try:
        columns = inspector.get_columns("chat")
        column_names = [col["name"] for col in columns]
        
        if "course_id" in column_names:
            op.drop_column("chat", "course_id")
    except Exception:
        pass  # Table might not exist
