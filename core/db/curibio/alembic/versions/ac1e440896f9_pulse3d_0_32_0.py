"""pulse3d 0.32.0

Revision ID: ac1e440896f9
Revises: eed0e6e02449
Create Date: 2023-03-20 18:10:57.535898

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "ac1e440896f9"
down_revision = "eed0e6e02449"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.32.0', 'testing')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.32.0'")
