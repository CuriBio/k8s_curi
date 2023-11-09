"""add preferences to users

Revision ID: c8b48ddce1ec
Revises: 511a7ede79a9
Create Date: 2023-11-10 08:12:30.738960

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c8b48ddce1ec"
down_revision = "511a7ede79a9"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("users", "data", new_column_name="preferences", server_default="{}")
    op.execute("UPDATE users SET preferences='{}'")


def downgrade():
    op.alter_column("users", "preferences", new_column_name="data", server_default=None)
    op.execute("UPDATE users SET data=NULL")
