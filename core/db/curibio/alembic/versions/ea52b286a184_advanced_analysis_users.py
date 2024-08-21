"""advanced-analysis users

Revision ID: ea52b286a184
Revises: 582a11bd1477
Create Date: 2024-08-20 08:50:41.532809

"""

import os

from alembic import op


# revision identifiers, used by Alembic.
revision = "ea52b286a184"
down_revision = "582a11bd1477"
branch_labels = None
depends_on = None


def upgrade():
    advanced_analysis_user_pass = os.getenv("ADVANCED_ANALYSIS_PASS")
    if advanced_analysis_user_pass is None:
        raise Exception("Missing required value for ADVANCED_ANALYSIS_PASS")
    aaqp_user_pass = os.getenv("ADVANCED_ANALYSIS_QUEUE_PROCESSOR_RO_PASS")
    if aaqp_user_pass is None:
        raise Exception("Missing required value for ADVANCED_ANALYSIS_QUEUE_PROCESSOR_RO_PASS")

    op.execute(f"CREATE USER curibio_advanced_analysis WITH PASSWORD '{advanced_analysis_user_pass}'")
    op.execute("GRANT ALL PRIVILEGES ON TABLE jobs_queue TO curibio_advanced_analysis")
    op.execute("GRANT ALL PRIVILEGES ON TABLE advanced_analysis_result TO curibio_advanced_analysis")
    op.execute("GRANT SELECT ON TABLE jobs_result TO curibio_advanced_analysis")
    op.execute("GRANT SELECT ON TABLE uploads TO curibio_advanced_analysis")

    op.execute(f"CREATE USER advanced_analysis_queue_processor_ro WITH PASSWORD '{aaqp_user_pass}'")
    op.execute("GRANT SELECT ON TABLE jobs_queue TO advanced_analysis_queue_processor_ro")


def downgrade():
    op.execute("REVOKE ALL PRIVILEGES ON TABLE jobs_queue FROM curibio_advanced_analysis")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE advanced_analysis_result FROM curibio_advanced_analysis")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE jobs_result FROM curibio_advanced_analysis")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE uploads FROM curibio_advanced_analysis")
    op.execute("DROP USER curibio_advanced_analysis")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE jobs_queue FROM advanced_analysis_queue_processor_ro")
    op.execute("DROP USER advanced_analysis_queue_processor_ro")
