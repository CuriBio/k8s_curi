"""pulse3d 0.34.2

Revision ID: 5a072ec334a3
Revises: b9df02413dd3
Create Date: 2023-09-06 10:56:38.381565

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "5a072ec334a3"
down_revision = "b9df02413dd3"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.34.2', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.34.2'")
