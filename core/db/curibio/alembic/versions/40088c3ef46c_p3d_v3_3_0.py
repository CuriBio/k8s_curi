"""p3d v3.3.0

Revision ID: 40088c3ef46c
Revises: 20a14bbe8069
Create Date: 2026-01-12 12:14:59.477161

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "40088c3ef46c"
down_revision = "20a14bbe8069"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('3.3.0', 'testing')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='3.3.0'")
