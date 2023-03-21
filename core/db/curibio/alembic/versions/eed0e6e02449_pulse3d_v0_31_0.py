"""pulse3d v0.31.0

Revision ID: eed0e6e02449
Revises: b1c798d03073
Create Date: 2023-03-16 13:04:53.372826

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "eed0e6e02449"
down_revision = "b1c798d03073"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.31.0', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.31.0'")
