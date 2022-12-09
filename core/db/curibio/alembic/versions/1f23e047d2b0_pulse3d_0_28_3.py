"""pulse3d_0_28_3

Revision ID: 1f23e047d2b0
Revises: 76a9da99875b
Create Date: 2022-12-09 14:35:40.222575

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1f23e047d2b0"
down_revision = "76a9da99875b"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.28.3', 'testing')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.28.3'")
