"""allow null for user passwords and add link column

Revision ID: e7b1c23cdb33
Revises: 323696292448
Create Date: 2022-11-22 15:01:20.153854

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e7b1c23cdb33"
down_revision = "323696292448"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("password", nullable=True)
        batch_op.add_column(sa.Column("pw_reset_verify_link", sa.VARCHAR(500), nullable=True))


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("password", nullable=False)
        batch_op.drop_column("pw_reset_verify_link")
