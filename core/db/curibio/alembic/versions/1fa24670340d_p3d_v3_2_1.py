"""p3d v3.2.1

Revision ID: 1fa24670340d
Revises: f64d3de27209
Create Date: 2025-10-31 12:34:14.433082

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "1fa24670340d"
down_revision = "f64d3de27209"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('3.2.1', 'testing')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='3.2.1'")
