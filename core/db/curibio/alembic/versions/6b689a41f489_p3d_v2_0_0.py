"""p3d v2.0.0

Revision ID: 6b689a41f489
Revises: f6fc3ccd01e2
Create Date: 2024-10-11 12:36:58.402604

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "6b689a41f489"
down_revision = "f6fc3ccd01e2"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('2.0.0', 'testing')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='2.0.0'")
