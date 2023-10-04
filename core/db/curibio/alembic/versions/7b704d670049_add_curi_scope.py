"""add curi scope

Revision ID: 7b704d670049
Revises: 3457f3c76e11
Create Date: 2023-10-05 09:26:55.386412

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "7b704d670049"
down_revision = "36891004f3e6"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "INSERT INTO account_scopes VALUES ((SELECT id FROM customers WHERE email='software@curibio.com'), NULL, 'curi:admin')"
    )


def downgrade():
    op.execute("DELETE FROM account_scopes WHERE scope='curi:admin'")
