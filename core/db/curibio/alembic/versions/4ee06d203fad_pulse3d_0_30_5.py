"""pulse3d 0.30.5

Revision ID: 4ee06d203fad
Revises: b1c798d03073
Create Date: 2023-03-13 21:45:31.213567

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "4ee06d203fad"
down_revision = "b1c798d03073"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.30.5', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.30.5'")
