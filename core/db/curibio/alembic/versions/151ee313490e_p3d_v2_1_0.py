"""p3d v2.1.0

Revision ID: 151ee313490e
Revises: 3f4112ab9f1b
Create Date: 2025-08-21 11:46:07.445952

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "151ee313490e"
down_revision = "3f4112ab9f1b"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('2.1.0', 'testing')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='2.1.0'")
