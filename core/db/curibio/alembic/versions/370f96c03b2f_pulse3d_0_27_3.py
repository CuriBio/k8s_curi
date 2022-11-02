"""pulse3D 0.27.3

Revision ID: 370f96c03b2f
Revises: da5a93c1bb08
Create Date: 2022-11-01 12:26:02.145745

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "370f96c03b2f"
down_revision = "da5a93c1bb08"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.27.3', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.27.3'")
