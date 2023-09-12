"""pulse3d 0.33.14

Revision ID: d1b668faadba
Revises: eb262a8603eb
Create Date: 2023-08-22 09:59:01.381911

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "d1b668faadba"
down_revision = "eb262a8603eb"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.33.14', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.33.14'")
