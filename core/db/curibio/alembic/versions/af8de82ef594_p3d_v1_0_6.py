"""p3d v1.0.6

Revision ID: af8de82ef594
Revises: f6f483c2b52e
Create Date: 2024-07-11 12:39:03.193977

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "af8de82ef594"
down_revision = "f6f483c2b52e"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('1.0.6', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='1.0.6'")
