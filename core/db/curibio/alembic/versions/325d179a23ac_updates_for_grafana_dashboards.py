"""Updates for grafana dashboards

Revision ID: 325d179a23ac
Revises: 0c8fe377c814
Create Date: 2024-02-14 12:24:02.152393

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "325d179a23ac"
down_revision = "0c8fe377c814"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("GRANT SELECT ON TABLE jobs_queue TO grafana_ro")

    with op.batch_alter_table("jobs_result") as batch_op:
        batch_op.add_column(sa.Column("started_at", sa.DateTime(timezone=False), nullable=True)),


def downgrade():
    op.execute("REVOKE ALL PRIVILEGES ON TABLE jobs_queue FROM grafana_ro")

    with op.batch_alter_table("jobs_result") as batch_op:
        batch_op.drop_column("started_at")
