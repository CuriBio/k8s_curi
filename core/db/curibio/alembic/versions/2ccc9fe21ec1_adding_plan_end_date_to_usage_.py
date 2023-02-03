"""Adding plan end date to usage_restrictions json object structure
Revision ID: 2ccc9fe21ec1
Revises: 89e819e0ecc2
Create Date: 2023-01-25 14:40:08.612570
"""
from alembic import op
import json


# revision identifiers, used by Alembic.
revision = "2ccc9fe21ec1"
down_revision = "89e819e0ecc2"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        f"UPDATE customers SET usage_restrictions = ' { json.dumps({'pulse3d': {'uploads': -1, 'jobs': -1,'expiration_date':None}})} ' "
    )


def downgrade():
    op.execute(
        f"UPDATE customers SET usage_restrictions = ' { json.dumps({'pulse3d': {'uploads': -1, 'jobs': -1}})} ' "
    )