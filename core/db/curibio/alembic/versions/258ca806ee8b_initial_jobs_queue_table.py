"""initial jobs queue table

Revision ID: 258ca806ee8b
Revises: 
Create Date: 2022-03-14 15:32:48.959338

"""
from alembic import op
from alembic import context
from sqlalchemy.sql import func
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa

config = context.config

# revision identifiers, used by Alembic.
revision = '258ca806ee8b'
down_revision = 'be5bfe07156a'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE USER curibio_jobs")
    op.execute("CREATE USER curibio_jobs_ro")

    op.create_table(
        'jobs',
        sa.Column("row_id", sa.Integer(), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), unique=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("queue", sa.String(32), nullable=False),
        sa.Column("priority", sa.Integer(), default=1, nullable=False),
        sa.Column("status", sa.Enum("uploading", "pending", "running", "finished", "error", "paused", name="JobStatus", create_type=True), nullable=False, server_default="pending"),
        sa.Column("details", sa.String(64), nullable=True),
        sa.Column("meta", postgresql.JSONB, server_default="{}", nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=False), server_default=func.now(), onupdate=func.now()),
    )

    op.execute("GRANT ALL PRIVILEGES ON jobs TO curibio_jobs")
    op.execute("GRANT USAGE ON SEQUENCE jobs_row_id_seq TO curibio_jobs")
    op.execute("GRANT SELECT ON jobs TO curibio_jobs_ro")

    table_user_pass = config.get_main_option("table_user_pass")
    table_user_pass_ro = config.get_main_option("table_user_pass_ro")

    op.execute(f"ALTER ROLE curibio_jobs WITH PASSWORD '{table_user_pass}'")
    op.execute(f"ALTER ROLE curibio_jobs_ro WITH PASSWORD '{table_user_pass_ro}'")


def downgrade():
    op.execute("REVOKE USAGE ON SEQUENCE jobs_row_id_seq FROM curibio_jobs")
    op.execute("REVOKE ALL PRIVILEGES ON jobs FROM curibio_jobs")
    op.execute("REVOKE ALL PRIVILEGES ON jobs FROM curibio_jobs_ro")
    op.execute("DROP USER curibio_jobs")
    op.execute("DROP USER curibio_jobs_ro")

    op.drop_table("jobs")
    op.execute('DROP TYPE "JobStatus"')
