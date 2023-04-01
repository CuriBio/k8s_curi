"""add auto_upload column to uploads

Revision ID: 827f22860c04
Revises: 04bfacd4385d
Create Date: 2023-03-28 11:59:57.441365

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "827f22860c04"
down_revision = "04bfacd4385d"
branch_labels = None
depends_on = None


def upgrade():
    # leaving nullable to differentiate uploads from before this migration where the original upload location is unknown
    op.add_column("uploads", sa.Column("auto_upload", sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column("uploads", "auto_upload")
