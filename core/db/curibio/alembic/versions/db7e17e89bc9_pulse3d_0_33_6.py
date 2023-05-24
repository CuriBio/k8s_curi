"""pulse3d 0.33.6

Revision ID: db7e17e89bc9
Revises: 379ff7797813
Create Date: 2023-05-12 09:12:53.461539

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "db7e17e89bc9"
down_revision = "379ff7797813"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.33.6', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.33.6'")
