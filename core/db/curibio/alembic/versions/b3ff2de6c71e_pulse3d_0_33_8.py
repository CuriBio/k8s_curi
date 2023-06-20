"""pulse3d 0.33.8

Revision ID: b3ff2de6c71e
Revises: 379ff7797813
Create Date: 2023-06-16 10:11:15.025691

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "b3ff2de6c71e"
down_revision = "379ff7797813"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.33.8', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.33.8'")
