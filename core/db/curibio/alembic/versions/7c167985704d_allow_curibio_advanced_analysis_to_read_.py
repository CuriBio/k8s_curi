"""allow curibio_advanced_analysis to read from customers

Revision ID: 7c167985704d
Revises: cdd5044068bd
Create Date: 2024-09-03 15:54:56.869125

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "7c167985704d"
down_revision = "cdd5044068bd"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("GRANT SELECT ON TABLE customers TO curibio_advanced_analysis")


def downgrade():
    op.execute("REVOKE ALL PRIVILEGES ON TABLE customers FROM curibio_advanced_analysis")
