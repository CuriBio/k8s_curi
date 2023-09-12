"""initial jobs queue table

Revision ID: 258ca806ee8b
Revises:
Create Date: 2022-03-14 15:32:48.959338

"""
import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = "258ca806ee8b"
down_revision = "be5bfe07156a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "uploads",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=func.now(),
            onupdate=func.now(),  # Tanner (9/12/22): onupdate will not actually add a trigger to update this col in the DB. See revision 871f6d005d86 for how to add a trigger correctly
        ),
        sa.Column("meta", postgresql.JSONB, server_default="{}", nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "jobs_queue",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True
        ),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("queue", sa.String(32), nullable=False),
        sa.Column("priority", sa.Integer(), default=1, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now()),
        sa.Column("meta", postgresql.JSONB, server_default="{}", nullable=True),
        sa.ForeignKeyConstraint(["upload_id"], ["uploads.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "jobs_result",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "finished", "error", name="JobStatus", create=True),
            nullable=False,
            default=sa.text("pending"),
        ),
        sa.Column("meta", postgresql.JSONB, server_default="{}", nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=False), server_default=func.now()),
        sa.Column("runtime", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["upload_id"], ["uploads.id"], ondelete="CASCADE"),
    )

    jobs_user_pass = os.getenv("JOBS_USER_PASS")
    if jobs_user_pass is None:
        raise Exception("Missing required value for JOBS_USER_PASS")

    jobs_user_pass_ro = os.getenv("JOBS_USER_PASS_RO")
    if jobs_user_pass_ro is None:
        raise Exception("Missing required value for JOBS_USER_PASS_RO")

    op.execute(f"CREATE USER curibio_jobs WITH PASSWORD '{jobs_user_pass}'")
    op.execute(f"CREATE USER curibio_jobs_ro WITH PASSWORD '{jobs_user_pass_ro}'")

    op.execute("GRANT ALL PRIVILEGES ON TABLE uploads TO curibio_jobs")
    op.execute("GRANT ALL PRIVILEGES ON TABLE jobs_queue TO curibio_jobs")
    op.execute("GRANT ALL PRIVILEGES ON TABLE jobs_result TO curibio_jobs")
    op.execute("GRANT SELECT ON TABLE users TO curibio_jobs")

    op.execute("GRANT USAGE ON SEQUENCE jobs_result_id_seq TO curibio_jobs")

    op.execute("GRANT SELECT ON TABLE uploads TO curibio_jobs_ro")
    op.execute("GRANT SELECT ON TABLE jobs_queue TO curibio_jobs_ro")
    op.execute("GRANT SELECT ON TABLE jobs_result TO curibio_jobs_ro")


def downgrade():
    op.execute("REVOKE USAGE ON SEQUENCE jobs_result_id_seq FROM curibio_jobs")

    op.execute("REVOKE ALL PRIVILEGES ON TABLE uploads FROM curibio_jobs")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE jobs_queue FROM curibio_jobs")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE jobs_result FROM curibio_jobs")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE users FROM curibio_jobs")

    op.execute("REVOKE ALL PRIVILEGES ON TABLE uploads FROM curibio_jobs_ro")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE jobs_queue FROM curibio_jobs_ro")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE jobs_result FROM curibio_jobs_ro")

    op.execute("DROP USER curibio_jobs")
    op.execute("DROP USER curibio_jobs_ro")

    op.execute("DROP TABLE uploads CASCADE")
    op.drop_table("jobs_queue")
    op.drop_table("jobs_result")
    op.execute('DROP TYPE "JobStatus"')
