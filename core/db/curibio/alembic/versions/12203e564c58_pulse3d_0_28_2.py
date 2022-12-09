"""pulse3d 0.28.2

Revision ID: 12203e564c58
Revises: 76a9da99875b
Create Date: 2022-12-08 16:22:06.054166

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "12203e564c58"
down_revision = "76a9da99875b"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.28.2', 'external')")
    op.execute("UPDATE pulse3d_versions SET state='deprecated' WHERE version='0.28.1'")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.28.2'")
    op.execute("UPDATE pulse3d_versions SET state='external' WHERE version='0.28.1'")
