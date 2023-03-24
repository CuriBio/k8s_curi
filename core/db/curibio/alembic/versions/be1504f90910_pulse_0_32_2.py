"""pulse_0_32_2

Revision ID: be1504f90910
Revises: 04bfacd4385d
Create Date: 2023-03-23 12:00:12.650271

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "be1504f90910"
down_revision = "04bfacd4385d"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.32.2', 'testing')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.32.2'")
