"""remove default last_login

Revision ID: 560e2d969290
Revises: 325d179a23ac
Create Date: 2024-03-04 10:51:13.864235

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "560e2d969290"
down_revision = "325d179a23ac"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE customers ALTER COLUMN last_login SET DEFAULT NULL")
    op.execute("ALTER TABLE users ALTER COLUMN last_login SET DEFAULT NULL")


def downgrade():
    op.execute("ALTER TABLE customers ALTER COLUMN last_login SET DEFAULT NOW()")
    op.execute("ALTER TABLE users ALTER COLUMN last_login SET DEFAULT NOW()")
