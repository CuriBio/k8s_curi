"""p3d v3.0.1

Revision ID: 8725946e754a
Revises: d68df89254b4
Create Date: 2025-10-10 12:20:09.481896

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "8725946e754a"
down_revision = "d68df89254b4"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('3.0.1', 'testing')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='3.0.1'")
