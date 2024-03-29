"""pulse3d 0.28.1

Revision ID: 04c57d3482e3
Revises: e7b1c23cdb33
Create Date: 2022-11-29 14:23:28.198412

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "04c57d3482e3"
down_revision = "e7b1c23cdb33"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.28.1', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.28.1'")
