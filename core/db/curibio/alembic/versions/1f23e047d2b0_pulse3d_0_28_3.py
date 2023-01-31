"""pulse3d_0_28_3

Revision ID: 1f23e047d2b0
Revises: 12203e564c58
Create Date: 2022-12-09 14:35:40.222575

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "1f23e047d2b0"
down_revision = "12203e564c58"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.28.3', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.28.3'")
