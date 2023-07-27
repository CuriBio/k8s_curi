"""add failed pass attemps column

Revision ID: 316e4d5eb991
Revises: 4c5b40dd7e96
Create Date: 2023-07-27 10:17:29.263357

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "316e4d5eb991"
down_revision = "4c5b40dd7e96"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("customers", "users"):
        op.add_column(
            table, sa.Column("failed_login_attempts", sa.INTEGER(), server_default="0", nullable=False)
        )


def downgrade():
    for table in ("customers", "users"):
        op.drop_column(table, "failed_login_attempts")
