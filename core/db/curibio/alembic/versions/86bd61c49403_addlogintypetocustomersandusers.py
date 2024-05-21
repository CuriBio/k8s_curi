"""addLoginTypeToCustomersAndUsers

Revision ID: 86bd61c49403
Revises: 848fb69a8766
Create Date: 2024-05-21 10:51:30.168752

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '86bd61c49403'
down_revision = '848fb69a8766'
branch_labels = None
depends_on = None
login_types = ("password", "sso_microsoft")
tables = ("customers", "users")


def upgrade():
    op.execute(f'CREATE TYPE "LoginType" AS ENUM {login_types}')

    for table in tables:
        op.add_column(
            table,
            sa.Column(
                "login_type",
                sa.Enum(*login_types, name="LoginType"),
                server_default=login_types[0],
                nullable=False,
            )
        )


def downgrade():
    for table in tables:
        op.drop_column(table, "login_type")

    op.execute('DROP TYPE "LoginType" CASCADE')
