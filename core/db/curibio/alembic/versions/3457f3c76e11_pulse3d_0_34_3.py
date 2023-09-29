"""pulse3d 0.34.3

Revision ID: 3457f3c76e11
Revises: 35e6c6b7ec8e
Create Date: 2023-09-27 09:59:37.295911

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "3457f3c76e11"
down_revision = "35e6c6b7ec8e"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.34.3', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.34.3'")
