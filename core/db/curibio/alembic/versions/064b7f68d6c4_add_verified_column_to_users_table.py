"""add verified column to users table

Revision ID: 064b7f68d6c4
Revises: c1ae9bb9fa14
Create Date: 2022-10-01 11:40:21.861502

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "064b7f68d6c4"
down_revision = "c1ae9bb9fa14"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("verified", sa.Boolean(), server_default="f"))
    op.execute("UPDATE users SET verified='t'")


def downgrade():
    op.drop_column("users", "verified")
