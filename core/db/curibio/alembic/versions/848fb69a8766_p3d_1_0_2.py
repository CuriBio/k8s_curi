"""p3d 1.0.2

Revision ID: 848fb69a8766
Revises: dd26b8c61f99
Create Date: 2024-04-04 12:49:49.726226

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "848fb69a8766"
down_revision = "dd26b8c61f99"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('1.0.2', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='1.0.2'")
