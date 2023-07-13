"""add admin account alias

Revision ID: 6d6d7d612cd1
Revises: c3ab9e9629ce
Create Date: 2023-07-12 16:44:49.087101

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "6d6d7d612cd1"
down_revision = "c3ab9e9629ce"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE customers ADD COLUMN id_alias VARCHAR(128)")


def downgrade():
    op.execute("ALTER TABLE customers DROP COLUMN id_alias")
