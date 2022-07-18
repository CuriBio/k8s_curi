"""empty message

Revision ID: 93ab16c01f9d
Revises: 3a2553a6d4b2
Create Date: 2022-07-18 12:23:28.863112

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "93ab16c01f9d"
down_revision = "3a2553a6d4b2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dummy",
        sa.Column("test", sa.String(12), primary_key=True),
    )


def downgrade():
    op.drop_table("dummy")
