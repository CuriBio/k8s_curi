"""pulse3d 0.25.4

Revision ID: c1ae9bb9fa14
Revises: 871f6d005d86
Create Date: 2022-09-23 10:57:43.588260

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "c1ae9bb9fa14"
down_revision = "871f6d005d86"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version) VALUES ('0.25.4')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version == '0.25.4'")
