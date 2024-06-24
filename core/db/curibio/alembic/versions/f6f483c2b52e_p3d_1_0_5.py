"""p3d 1.0.5

Revision ID: f6f483c2b52e
Revises: c8c266af4275
Create Date: 2024-06-24 16:05:18.697899

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "f6f483c2b52e"
down_revision = "c8c266af4275"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('1.0.5', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='1.0.5'")
