"""add plan end date

Revision ID: be675b881e83
Revises: f1d027786249
Create Date: 2023-02-06 12:54:34.261103

"""
from alembic import op
import json


# revision identifiers, used by Alembic.
revision = "be675b881e83"
down_revision = "f1d027786249"
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
