"""pulse3d_0.34.4

Revision ID: 511a7ede79a9
Revises: 82cfce33cc20
Create Date: 2023-10-31 13:24:09.433848

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "511a7ede79a9"
down_revision = "82cfce33cc20"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version) VALUES ('0.34.4')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.34.4'")
