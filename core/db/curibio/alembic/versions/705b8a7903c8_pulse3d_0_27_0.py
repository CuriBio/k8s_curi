"""pulse3d 0.27.0

Revision ID: 705b8a7903c8
Revises: c1ae9bb9fa14
Create Date: 2022-10-06 10:42:13.286377

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "705b8a7903c8"
down_revision = "c1ae9bb9fa14"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version) VALUES ('0.27.0')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.27.0'")
