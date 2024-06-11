"""p3d v1.0.4

Revision ID: 34ba5254bfe1
Revises: 86bd61c49403
Create Date: 2024-06-06 14:00:49.232680

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "34ba5254bfe1"
down_revision = "86bd61c49403"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('1.0.4', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='1.0.4'")
