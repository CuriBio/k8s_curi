"""pulse3d 0.30.2

Revision ID: ee5a045faeac
Revises: b1c798d03073
Create Date: 2023-02-22 20:06:54.120457

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "ee5a045faeac"
down_revision = "b1c798d03073"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.30.2', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.30.2'")
