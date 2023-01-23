"""add pulse3d version 0.29.1

Revision ID: d7a72568d90b
Revises: 1f23e047d2b0
Create Date: 2023-01-19 15:02:57.165859

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "d7a72568d90b"
down_revision = "1f23e047d2b0"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.29.1', 'external')")
    op.execute("UPDATE pulse3d_versions SET state='deprecated' WHERE version='0.29.0'")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.29.1'")
    op.execute("UPDATE pulse3d_versions SET state='external' WHERE version='0.29.0'")
