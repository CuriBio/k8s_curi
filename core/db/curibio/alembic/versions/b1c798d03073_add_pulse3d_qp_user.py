"""add pulse3d queue processor user

Revision ID: b1c798d03073
Revises: be675b881e83
Create Date: 2023-02-03 07:37:51.357347

"""
from alembic import op
import os

# revision identifiers, used by Alembic.
revision = "b1c798d03073"
down_revision = "be675b881e83"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        f"CREATE USER pulse3d_queue_processor_ro WITH PASSWORD '{os.getenv('PULSE3D_QUEUE_PROCESSOR_RO_PASS')}'"
    )
    op.execute("GRANT SELECT ON TABLE jobs_queue TO pulse3d_queue_processor_ro")


def downgrade():
    op.execute("REVOKE ALL PRIVILEGES ON TABLE jobs_queue FROM pulse3d_queue_processor_ro")
    op.execute("DROP USER pulse3d_queue_processor_ro")
