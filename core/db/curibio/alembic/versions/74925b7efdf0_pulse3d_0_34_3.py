"""pulse3d 0.34.3

Revision ID: 74925b7efdf0
Revises: 95c63cf51c4a
Create Date: 2023-09-26 10:37:15.516585

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "74925b7efdf0"
down_revision = "95c63cf51c4a"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.34.3', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.34.3'")
