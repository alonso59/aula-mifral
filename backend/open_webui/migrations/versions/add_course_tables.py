"""Add course tables

Revision ID: add_course_tables
Revises: 3781e22d8b01
Create Date: 2025-01-03 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "add_course_tables"
down_revision = "3781e22d8b01"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    # Create course table only if it doesn't exist
    if "course" not in tables:
        op.create_table(
            "course",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("main_topics", sa.JSON(), nullable=True),
            sa.Column("objectives", sa.JSON(), nullable=True),
            sa.Column("files", sa.JSON(), nullable=True),
            sa.Column("links", sa.JSON(), nullable=True),
            sa.Column("tasks", sa.JSON(), nullable=True),
            sa.Column("youtube_url", sa.Text(), nullable=True),
            sa.Column("access_control", sa.JSON(), nullable=True),
            sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )

    # Create course_doc table only if it doesn't exist
    if "course_doc" not in tables:
        op.create_table(
            "course_doc",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
            sa.Column("course_id", sa.Text(), nullable=False),
            sa.Column("file_id", sa.Text(), nullable=False),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("mime_type", sa.Text(), nullable=True),
            sa.Column("storage_uri", sa.Text(), nullable=True),
            sa.Column("chunk_config", sa.JSON(), nullable=True),
            sa.Column("embed_status", sa.Text(), default="pending", nullable=False),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )

    # Create enrollment table only if it doesn't exist
    if "enrollment" not in tables:
        op.create_table(
            "enrollment",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
            sa.Column("course_id", sa.Text(), nullable=False),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column("role", sa.Text(), nullable=False),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )

    # Create student_feedback table only if it doesn't exist
    if "student_feedback" not in tables:
        op.create_table(
            "student_feedback",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
            sa.Column("course_id", sa.Text(), nullable=False),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )

    # Add course_id to chat table (check if column doesn't already exist)
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
    # Remove course_id from chat table (check if column exists first)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if chat table exists and has course_id column
    try:
        columns = inspector.get_columns("chat")
        column_names = [col["name"] for col in columns]
        
        if "course_id" in column_names:
            op.drop_column("chat", "course_id")
    except Exception:
        pass  # Table might not exist
    
    # Check which tables exist before dropping
    tables = inspector.get_table_names()
    
    # Drop course-related tables in reverse order (only if they exist)
    if "student_feedback" in tables:
        op.drop_table("student_feedback")
    if "enrollment" in tables:
        op.drop_table("enrollment")
    if "course_doc" in tables:
        op.drop_table("course_doc")
    if "course" in tables:
        op.drop_table("course")
