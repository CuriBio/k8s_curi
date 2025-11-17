"""p3d v3.2.2

Revision ID: e6e3b358784c
Revises: 1fa24670340d
Create Date: 2025-11-17 12:12:17.730142

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "e6e3b358784c"
down_revision = "1fa24670340d"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('3.2.2', 'testing')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='3.2.2'")
