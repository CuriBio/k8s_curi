"""pulse3d 0.33.9

Revision ID: 0c9728b0804e
Revises: b3ff2de6c71e
Create Date: 2023-06-24 10:34:44.596025

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0c9728b0804e"
down_revision = "b3ff2de6c71e"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.33.9', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.33.9'")
