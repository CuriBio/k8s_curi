"""test 

Revision ID: 5b9e566ac996
Revises: 5b1cb92fa435
Create Date: 2022-08-29 11:03:07.338427

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5b9e566ac996"
down_revision = "5b1cb92fa435"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("test", sa.Column("test", sa.String(12), primary_key=True))


def downgrade():
    op.drop_table("test")
