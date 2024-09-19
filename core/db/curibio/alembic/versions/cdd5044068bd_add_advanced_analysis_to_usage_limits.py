"""add advanced analysis to usage limits

Revision ID: cdd5044068bd
Revises: a316cdf0e2db
Create Date: 2024-08-29 13:55:39.078094

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "cdd5044068bd"
down_revision = "a316cdf0e2db"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        UPDATE customers
        SET usage_restrictions=usage_restrictions||'{"advanced_analysis": {"jobs": -1, "expiration_date": null}}'::jsonb
        WHERE usage_restrictions IS NOT NULL
        """
    )


def downgrade():
    op.execute(
        """
        UPDATE customers
        SET usage_restrictions=usage_restrictions - 'advanced_analysis'
        WHERE usage_restrictions IS NOT NULL
        """
    )
