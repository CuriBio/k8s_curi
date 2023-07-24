"""customer account alias

Revision ID: 4c5b40dd7e96
Revises: c3ab9e9629ce
Create Date: 2023-07-24 08:05:56.598736

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "4c5b40dd7e96"
down_revision = "c3ab9e9629ce"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE customers ADD COLUMN alias VARCHAR(128)")
    op.execute("ALTER TABLE customers ADD CONSTRAINT customers_alias_key UNIQUE (alias)")


def downgrade():
    op.execute("ALTER TABLE customers DROP COLUMN alias")
