"""p3d v3.2.0

Revision ID: f64d3de27209
Revises: 8725946e754a
Create Date: 2025-10-13 16:00:10.115493

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "f64d3de27209"
down_revision = "8725946e754a"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('3.2.0', 'testing')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='3.2.0'")
