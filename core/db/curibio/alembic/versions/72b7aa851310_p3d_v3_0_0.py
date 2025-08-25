"""p3d v3.0.0

Revision ID: 72b7aa851310
Revises: 151ee313490e
Create Date: 2025-08-25 11:37:47.654217

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "72b7aa851310"
down_revision = "151ee313490e"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('3.0.0', 'beta')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='3.0.0'")
