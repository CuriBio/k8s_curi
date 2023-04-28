"""pulse3d 0.32.6

Revision ID: 6ae5abb40525
Revises: 3ffac4d68585
Create Date: 2023-04-28 14:16:24.334842

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "6ae5abb40525"
down_revision = "3ffac4d68585"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.32.6', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.32.6'")
