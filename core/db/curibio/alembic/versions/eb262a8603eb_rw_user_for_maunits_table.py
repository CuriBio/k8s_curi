"""RW user for maunits table

Revision ID: eb262a8603eb
Revises: 316e4d5eb991
Create Date: 2023-08-15 10:44:25.814417

"""
import os
from alembic import op


# revision identifiers, used by Alembic.
revision = "eb262a8603eb"
down_revision = "316e4d5eb991"
branch_labels = None
depends_on = None


def upgrade():
    mantarray_user_pass = os.getenv("MANTARRAY_USER_PASS")
    if not mantarray_user_pass:
        raise Exception("Missing required value for MANTARRAY_USER_PASS")

    op.execute(f"CREATE USER curibio_mantarray WITH PASSWORD '{mantarray_user_pass}'")
    op.execute("GRANT ALL PRIVILEGES ON TABLE maunits TO curibio_mantarray")


def downgrade():
    op.execute("REVOKE ALL PRIVILEGES ON TABLE maunits FROM curibio_mantarray")
    op.execute("DROP USER curibio_mantarray")
