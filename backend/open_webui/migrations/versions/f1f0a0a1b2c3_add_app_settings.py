"""add app_settings table and seed classroom_mode

Revision ID: f1f0a0a1b2c3
Revises: e4c7a8b0f9d1
Create Date: 2025-08-08
"""

from alembic import op
import sqlalchemy as sa
import time

# revision identifiers, used by Alembic.
revision = 'f1f0a0a1b2c3'
down_revision = 'e4c7a8b0f9d1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'app_settings' not in tables:
        op.create_table(
            'app_settings',
            sa.Column('key', sa.String(), primary_key=True),
            sa.Column('value', sa.JSON(), nullable=True),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )

    # Seed CLASSROOM_MODE row if not exists
    conn = op.get_bind()
    res = conn.execute(sa.text("SELECT key FROM app_settings WHERE key='CLASSROOM_MODE'"))
    if res.first() is None:
        conn.execute(
            sa.text("INSERT INTO app_settings(key, value, updated_at) VALUES (:k, :v, :t)")
            , { 'k': 'CLASSROOM_MODE', 'v': '{"enabled": false}', 't': int(time.time()) }
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if 'app_settings' in tables:
        op.drop_table('app_settings')
