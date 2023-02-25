"""pulse3d 0.30.3

Revision ID: f5ceb7c8cea1
Revises: ee5a045faeac
Create Date: 2023-02-25 14:42:02.814724

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f5ceb7c8cea1'
down_revision = 'ee5a045faeac'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.30.3', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.30.3'")
