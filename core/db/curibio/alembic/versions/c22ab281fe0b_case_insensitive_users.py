"""case insensitive users

Revision ID: c22ab281fe0b
Revises: 370f96c03b2f
Create Date: 2022-11-08 14:36:15.713016

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "c22ab281fe0b"
down_revision = "370f96c03b2f"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE users SET name = LOWER(name)")


def downgrade():
    # this cannot be undone as the cases used in the original usernames are lost
    pass
