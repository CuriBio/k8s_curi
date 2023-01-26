"""Adding plan end date to usage_restrictions json object structure

Revision ID: 2ccc9fe21ec1
Revises: 1f23e047d2b0
Create Date: 2023-01-25 14:40:08.612570

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2ccc9fe21ec1"
down_revision = "1f23e047d2b0"
branch_labels = None
depends_on = None


def upgrade():
    new_usage_restrictions_struct = {"pulse3d": {"jobs": -1, "uploads": -1, "end": None}}
    op.execute(f"UPDATE customers SET usage_restrictions = {new_usage_restrictions_struct}")


def downgrade():
    old_usage_restrictions = {
        "pulse3d": {
            "jobs": -1,
            "uploads": -1,
        }
    }
    op.execute(f"UPDATE customers SET usage_restrictions = {old_usage_restrictions}")
