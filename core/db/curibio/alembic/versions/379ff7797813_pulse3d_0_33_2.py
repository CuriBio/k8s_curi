"""pulse3d 0.33.2

Revision ID: 379ff7797813
Revises: 6ae5abb40525
Create Date: 2023-05-05 14:22:13.366376

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "379ff7797813"
down_revision = "6ae5abb40525"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.33.2', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.33.2'")
