"""case insensitive users

Revision ID: c22ab281fe0b
Revises: 370f96c03b2f
Create Date: 2022-11-08 14:36:15.713016

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c22ab281fe0b"
down_revision = "370f96c03b2f"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE users set name = LOWER(name)")


def downgrade():
    pass
