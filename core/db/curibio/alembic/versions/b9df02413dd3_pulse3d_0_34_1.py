"""pulse3d 0.34.1

Revision ID: b9df02413dd3
Revises: d1b668faadba
Create Date: 2023-09-06 10:08:51.859187

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "b9df02413dd3"
down_revision = "d1b668faadba"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.34.1', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.34.1'")
