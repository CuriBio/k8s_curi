"""give curibio_event_broker select on jobs_result

Revision ID: 73f5610ab1fa
Revises: 9566734eccae
Create Date: 2024-08-20 17:43:09.076128

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "73f5610ab1fa"
down_revision = "9566734eccae"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("GRANT SELECT ON TABLE jobs_result TO curibio_event_broker")


def downgrade():
    op.execute("REVOKE ALL PRIVILEGES ON TABLE jobs_result FROM curibio_event_broker")
