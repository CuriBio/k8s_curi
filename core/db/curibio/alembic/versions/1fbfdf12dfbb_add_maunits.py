"""add MAUnits

Revision ID: 1fbfdf12dfbb
Revises: 258ca806ee8b
Create Date: 2022-03-16 21:42:22.132660

"""
import os
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1fbfdf12dfbb'
down_revision = '258ca806ee8b'
branch_labels = None
depends_on = None


def upgrade():
    table = op.create_table(
        "maunits",
        sa.Column("serial_number", sa.String(12), primary_key=True),
        sa.Column("hw_version", sa.String(12), nullable=False),
    )

    op.bulk_insert(table,
        [
            {"serial_number": "M02022055001", "hw_version": "2.2.0"},
            {"serial_number": "M02022055002", "hw_version": "2.2.0"},
            {"serial_number": "M02022055003", "hw_version": "2.2.0"},
            {"serial_number": "M02022055004", "hw_version": "2.2.0"},
        ],
    )

    mantarray_ro_pass = os.getenv("MANTARRAY_RO_PASS")
    if not mantarray_ro_pass:
        raise Exception("Missing requireed value for MANTARRAY_RO_PASS")

    op.execute(f"CREATE USER curibio_mantarray_ro WITH PASSWORD '{mantarray_ro_pass}'")
    op.execute("GRANT SELECT ON TABLE maunits TO curibio_mantarray_ro")


def downgrade():
    op.execute("REVOKE ALL PRIVILEGES ON TABLE maunits FROM curibio_mantarray_ro")
    op.drop_table("maunits")
    op.execute("DROP USER curibio_mantarray_ro")

