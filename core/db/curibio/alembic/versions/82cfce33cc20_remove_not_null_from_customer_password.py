"""remove not null from customer password

Revision ID: 82cfce33cc20
Revises: 36891004f3e6
Create Date: 2023-10-06 14:30:15.397100

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "82cfce33cc20"
down_revision = "36891004f3e6"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE customers ALTER COLUMN password DROP NOT NULL")


def downgrade():
    op.execute("ALTER TABLE customers ALTER COLUMN password SET NOT NULL")
