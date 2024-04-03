"""p3d 1.0.1

Revision ID: 8d1f3c536b6d
Revises: c8d1b4377985
Create Date: 2024-04-01 15:26:30.259748

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "8d1f3c536b6d"
down_revision = "c8d1b4377985"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('1.0.1', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='1.0.1'")
