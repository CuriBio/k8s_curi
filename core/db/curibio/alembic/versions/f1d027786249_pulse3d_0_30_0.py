"""pulse3d 0.30.0

Revision ID: f1d027786249
Revises: 89e819e0ecc2
Create Date: 2023-02-04 10:11:01.214992

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1d027786249'
down_revision = '89e819e0ecc2'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.30.0', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.30.0'")
