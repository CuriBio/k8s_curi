"""p3d v2.0.1

Revision ID: dbf4f67a6571
Revises: 309d3f752473
Create Date: 2025-08-08 12:28:38.901746

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "dbf4f67a6571"
down_revision = "309d3f752473"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('2.0.1', 'testing')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='2.0.1'")
