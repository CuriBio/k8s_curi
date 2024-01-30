"""Add state to SW versions

Revision ID: abc8d3935c1b
Revises: 2acde568c771
Create Date: 2024-01-25 11:04:48.959656

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "abc8d3935c1b"
down_revision = "2acde568c771"
branch_labels = None
depends_on = None


def upgrade():
    states = ("internal", "external")

    tables = ("ma_controllers", "sting_controllers")

    op.execute(f'CREATE TYPE "SoftwareState" AS ENUM {states}')

    for table in tables:
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "state",
                    sa.Enum(*states, name="SoftwareState", create_type=True),
                    server_default=states[0],
                    nullable=True,
                )
            )


def downgrade():
    tables = ("ma_controllers", "sting_controllers")
    for table in tables:
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_column("state")

    op.execute('DROP TYPE "SoftwareState" CASCADE')
