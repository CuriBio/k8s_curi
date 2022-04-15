"""create pulse3d tables

Revision ID: 49fceab10078
Revises: 1fbfdf12dfbb
Create Date: 2022-04-15 08:08:25.056643

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.sql import func

revision = "49fceab10078"
down_revision = "1fbfdf12dfbb"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "uploaded_s3_objects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bucket", sa.VARCHAR(255), nullable=False),
        sa.Column("object_key", sa.VARCHAR(255), nullable=False),
        sa.Column("md5_confirmed_after_upload_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("upload_interruptions", sa.Integer(), nullable=True),
        sa.Column("md5_failures", sa.Integer(), nullable=True),
        sa.Column(
            "upload_started_at",
            sa.DateTime(timezone=False),
            nullable=True,
        ),
        sa.Column("original_file_path", sa.VARCHAR(255), nullable=True),
        sa.Column("uploading_computer_name", sa.VARCHAR(255), nullable=True),
    )

    op.create_table(
        "s3_objects",
        sa.Column("upload_id", sa.Integer(), nullable=False),
        sa.Column("stored_at", sa.DateTime(timezone=False), server_default=func.now()),
        sa.Column("kilobytes", sa.BigInteger(), nullable=True),
        sa.Column("md5", sa.VARCHAR(255), nullable=True),
        sa.ForeignKeyConstraint(["upload_id"], ["uploaded_s3_objects.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "mantarray_recording_sessions",
        sa.Column(
            "mantarray_recording_session_id",
            pg.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("customer_account_id", sa.VARCHAR(255), nullable=False),
        sa.Column("user_account_id", sa.VARCHAR(255), nullable=True),
        sa.Column("session_log_id", sa.VARCHAR(255), nullable=True),
        sa.Column("instrument_serial_number", sa.VARCHAR(255), nullable=True),
        sa.Column("acquisition_started_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("length_microseconds", sa.BigInteger(), nullable=True),
        sa.Column("recording_started_at", sa.DateTime(timezone=False), nullable=True),
    )

    op.create_table(
        "mantarray_session_log_files",
        sa.Column("session_log_id", sa.VARCHAR(255), nullable=False),
        sa.Column("bucket", sa.VARCHAR(255), nullable=False),
        sa.Column("object_key", sa.VARCHAR(255), nullable=False),
        sa.Column("upload_id", sa.Integer(), nullable=True),
        sa.Column("mantarray_recording_session_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("software_version", sa.VARCHAR(255), nullable=True),
        sa.Column("file_format_version", sa.VARCHAR(255), nullable=True),
        sa.Column("customer_account_id", sa.VARCHAR(255), nullable=True),
        sa.Column("user_account_id", sa.VARCHAR(255), nullable=True),
        sa.ForeignKeyConstraint(["upload_id"], ["uploaded_s3_objects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["mantarray_recording_session_id"],
            ["mantarray_recording_sessions.mantarray_recording_session_id"],
            ondelete="SET NULL",
        ),
    )

    op.create_table(
        "mantarray_raw_files",
        sa.Column("well_index", sa.SmallInteger(), nullable=False),
        sa.Column("upload_id", sa.Integer(), nullable=True),
        sa.Column("length_microseconds", sa.BigInteger(), nullable=True),
        sa.Column("recording_started_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("mantarray_recording_session_id", pg.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["upload_id"], ["uploaded_s3_objects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["mantarray_recording_session_id"],
            ["mantarray_recording_sessions.mantarray_recording_session_id"],
            ondelete="SET NULL",
        ),
    )

    op.execute("GRANT USAGE ON SEQUENCE uploaded_s3_objects_id_seq TO curibio_jobs")

    op.execute("GRANT ALL PRIVILEGES ON TABLE uploaded_s3_objects TO curibio_jobs")
    op.execute("GRANT ALL PRIVILEGES ON TABLE s3_objects TO curibio_jobs")
    op.execute("GRANT ALL PRIVILEGES ON TABLE mantarray_recording_sessions TO curibio_jobs")
    op.execute("GRANT ALL PRIVILEGES ON TABLE mantarray_session_log_files TO curibio_jobs")
    op.execute("GRANT ALL PRIVILEGES ON TABLE mantarray_raw_files TO curibio_jobs")

    op.execute("GRANT SELECT ON TABLE uploaded_s3_objects TO curibio_jobs_ro")
    op.execute("GRANT SELECT ON TABLE s3_objects TO curibio_jobs_ro")
    op.execute("GRANT SELECT ON TABLE mantarray_recording_sessions TO curibio_jobs_ro")
    op.execute("GRANT SELECT ON TABLE mantarray_session_log_files TO curibio_jobs_ro")
    op.execute("GRANT SELECT ON TABLE mantarray_raw_files TO curibio_jobs_ro")


def downgrade():
    op.execute("REVOKE USAGE ON SEQUENCE uploaded_s3_objects_id_seq FROM curibio_jobs")

    op.execute("REVOKE ALL PRIVILEGES ON TABLE uploaded_s3_objects FROM curibio_jobs")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE s3_objects FROM curibio_jobs")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE mantarray_recording_sessions FROM curibio_jobs")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE mantarray_session_log_files FROM curibio_jobs")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE mantarray_raw_files FROM curibio_jobs")

    op.execute("REVOKE ALL PRIVILEGES ON TABLE uploaded_s3_objects FROM curibio_jobs_ro")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE s3_objects FROM curibio_jobs_ro")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE mantarray_recording_sessions FROM curibio_jobs_ro")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE mantarray_session_log_files FROM curibio_jobs_ro")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE mantarray_raw_files FROM curibio_jobs_ro")

    op.drop_table("s3_objects")
    op.drop_table("mantarray_session_log_files")
    op.drop_table("mantarray_raw_files")
    op.drop_table("mantarray_recording_sessions")
    op.drop_table("uploaded_s3_objects")
