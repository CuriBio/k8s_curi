"""pulse3d 0.34.5

Revision ID: c8d1b4377985
Revises: 560e2d969290
Create Date: 2024-03-11 11:59:18.704624

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "c8d1b4377985"
down_revision = "560e2d969290"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.34.5', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.34.5'")
