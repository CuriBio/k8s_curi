"""case insensitive customer aliases

Revision ID: 36891004f3e6
Revises: 3457f3c76e11
Create Date: 2023-10-05 07:05:37.995895

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "36891004f3e6"
down_revision = "3457f3c76e11"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE customers SET alias = LOWER(alias)")


def downgrade():
    pass
