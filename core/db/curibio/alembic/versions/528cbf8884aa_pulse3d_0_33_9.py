"""pulse3d 0.33.9
Revision ID: 528cbf8884aa
Revises: b3ff2de6c71e
Create Date: 2023-06-30 12:18:05.162411

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "528cbf8884aa"
down_revision = "b3ff2de6c71e"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.33.9', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.33.9'")
