"""add operator user

Revision ID: b1c798d03073
Revises: 2ccc9fe21ec1
Create Date: 2023-02-03 07:37:51.357347

"""
from alembic import op
import os

# revision identifiers, used by Alembic.
revision = "b1c798d03073"
down_revision = "2ccc9fe21ec1"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(f"CREATE USER curibio_operators_ro WITH PASSWORD '{os.getenv('OPERATORS_RO_PASS')}'")
    op.execute("GRANT SELECT ON TABLE jobs_queue TO curibio_operators_ro")


def downgrade():
    op.execute("REVOKE ALL PRIVILEGES ON TABLE jobs_queue FROM curibio_operators_ro")
    op.execute("DROP USER curibio_operators_ro")
