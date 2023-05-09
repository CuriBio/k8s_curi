"""pulse3d 0.32.5

Revision ID: 3ffac4d68585
Revises: 39405902fa31
Create Date: 2023-04-25 10:28:51.249718

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "3ffac4d68585"
down_revision = "39405902fa31"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.32.5', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.32.5'")
