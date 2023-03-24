"""pulse 0.32.1

Revision ID: 04bfacd4385d
Revises: 0b1999fb5ce5
Create Date: 2023-03-21 14:53:49.083859

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "04bfacd4385d"
down_revision = "0b1999fb5ce5"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.32.1', 'testing')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.32.1'")
