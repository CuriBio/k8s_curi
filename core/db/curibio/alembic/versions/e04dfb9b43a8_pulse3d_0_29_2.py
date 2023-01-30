"""pulse3d 0.29.2

Revision ID: e04dfb9b43a8
Revises: d7a72568d90b
Create Date: 2023-01-24 12:54:38.970419

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "e04dfb9b43a8"
down_revision = "d7a72568d90b"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.29.2', 'external')")
    op.execute("UPDATE pulse3d_versions SET state='deprecated' WHERE version='0.29.1'")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.29.2'")
    op.execute("UPDATE pulse3d_versions SET state='external' WHERE version='0.29.1'")
