"""add cloud usage column to customers table

Revision ID: 4aac7b465d29
Revises: 705b8a7903c8
Create Date: 2022-10-19 10:39:53.261901

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4aac7b465d29'
down_revision = '705b8a7903c8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("customers", sa.Column("usage_restrictions", postgresql.JSONB, server_default="{}", nullable=True))
    # default all existing to free pulse3d users
    op.execute("UPDATE users SET data = '{ "scope": ["pulse3d:user:free"] }' ")

    op.execute("UPDATE customers SET data = '{ "scope": ["pulse3d:customer:free"] }' AND usage_restrictions = '{"pulse3d": {"uploads": "10", "jobs": "20"}}'")


def downgrade():
    op.drop_column("customers", "usage_restrictions")
    op.execute("UPDATE users SET data = '{ "scope": ["users:free"] }' ")
