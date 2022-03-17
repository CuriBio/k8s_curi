"""add MAUnits

Revision ID: 1fbfdf12dfbb
Revises: 258ca806ee8b
Create Date: 2022-03-16 21:42:22.132660

"""
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


def downgrade():
    op.drop_table('MAUnits')
