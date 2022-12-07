"""adding password reset link to customer table

Revision ID: 76a9da99875b
Revises: e7b1c23cdb33
Create Date: 2022-12-07 10:44:53.989100

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "76a9da99875b"
down_revision = "e7b1c23cdb33"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("customers", sa.Column("pw_reset_link", sa.VARCHAR(500), nullable=True))


def downgrade():
    op.drop_column("customers", "pw_reset_link")
