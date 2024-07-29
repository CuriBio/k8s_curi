"""p3d v1.0.8

Revision ID: ba1300aff257
Revises: af8de82ef594
Create Date: 2024-07-29 11:48:17.860370

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "ba1300aff257"
down_revision = "af8de82ef594"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('1.0.8', 'external')")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='1.0.8'")
