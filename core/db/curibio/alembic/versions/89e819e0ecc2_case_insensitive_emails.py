"""case_insensitive_emails

Revision ID: 89e819e0ecc2
Revises: d7a72568d90b
Create Date: 2023-01-24 06:55:02.841578

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "89e819e0ecc2"
down_revision = "d7a72568d90b"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE users SET email = LOWER(email)")


def downgrade():
    # this cannot be undone as the cases used in the original usernames are lost
    pass
