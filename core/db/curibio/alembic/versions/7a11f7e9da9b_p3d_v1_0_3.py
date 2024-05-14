"""p3d v1.0.3

Revision ID: 7a11f7e9da9b
Revises: de4ec59b138a
Create Date: 2024-05-14 12:37:01.971989

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "7a11f7e9da9b"
down_revision = "de4ec59b138a"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('1.0.3', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='1.0.3'")
