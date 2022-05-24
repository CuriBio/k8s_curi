"""add refresh tokens

Revision ID: 6dbe71e474d2
Revises: 666e49886290
Create Date: 2022-05-24 12:53:05.802283

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6dbe71e474d2"
down_revision = "666e49886290"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("users", "customers"):
        op.add_column(table, sa.Column("refresh_token", sa.VARCHAR(255), nullable=True))


def downgrade():
    for table in ("users", "customers"):
        op.drop_column(table, "refresh_token")
