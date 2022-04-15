"""create pulse3d tables

Revision ID: 49fceab10078
Revises: 1fbfdf12dfbb
Create Date: 2022-04-15 08:08:25.056643

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "49fceab10078"
down_revision = "1fbfdf12dfbb"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("uploads") as batch_op:
        batch_op.add_column(sa.Column("bucket", sa.VARCHAR(255), nullable=False))
        batch_op.add_column(sa.Column("object_key", sa.VARCHAR(255), nullable=False))
        batch_op.add_column(sa.Column("original_file_path", sa.VARCHAR(255), nullable=True))
        batch_op.add_column(sa.Column("uploading_computer_name", sa.VARCHAR(255), nullable=True))
        batch_op.add_column(sa.Column("kilobytes", sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column("md5", sa.VARCHAR(255), nullable=True))

    op.create_table(
        "mantarray_recording_sessions",
        sa.Column(
            "mantarray_recording_session_id",
            pg.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("upload_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_account_id", sa.VARCHAR(255), nullable=False),
        sa.Column("user_account_id", sa.VARCHAR(255), nullable=True),
        sa.Column("session_log_id", sa.VARCHAR(255), nullable=True),
        sa.Column("instrument_serial_number", sa.VARCHAR(255), nullable=True),
        sa.Column("acquisition_started_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("length_microseconds", sa.BigInteger(), nullable=True),
        sa.Column("recording_started_at", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(["upload_id"], ["uploads.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "mantarray_session_log_files",
        sa.Column("session_log_id", sa.VARCHAR(255), nullable=False),
        sa.Column("bucket", sa.VARCHAR(255), nullable=False),
        sa.Column("object_key", sa.VARCHAR(255), nullable=False),
        sa.Column("upload_id", sa.Integer(), nullable=False),
        sa.Column("mantarray_recording_session_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("software_version", sa.VARCHAR(255), nullable=True),
        sa.Column("file_format_version", sa.VARCHAR(255), nullable=True),
        sa.Column("customer_account_id", sa.VARCHAR(255), nullable=True),
        sa.Column("user_account_id", sa.VARCHAR(255), nullable=True),
        sa.ForeignKeyConstraint(["upload_id"], ["uploads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["mantarray_recording_session_id"],
            ["mantarray_recording_sessions.mantarray_recording_session_id"],
            ondelete="SET NULL",
        ),
    )

    op.execute("GRANT ALL PRIVILEGES ON TABLE mantarray_recording_sessions TO curibio_jobs")
    op.execute("GRANT ALL PRIVILEGES ON TABLE mantarray_session_log_files TO curibio_jobs")

    op.execute("GRANT SELECT ON TABLE mantarray_recording_sessions TO curibio_jobs_ro")
    op.execute("GRANT SELECT ON TABLE mantarray_session_log_files TO curibio_jobs_ro")


def downgrade():
    op.execute("REVOKE ALL PRIVILEGES ON TABLE mantarray_recording_sessions FROM curibio_jobs")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE mantarray_session_log_files FROM curibio_jobs")

    op.execute("REVOKE ALL PRIVILEGES ON TABLE mantarray_recording_sessions FROM curibio_jobs_ro")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE mantarray_session_log_files FROM curibio_jobs_ro")

    op.drop_table("mantarray_session_log_files")
    op.drop_table("mantarray_recording_sessions")
    
    with op.batch_alter_table("uploads") as batch_op:
        batch_op.drop_column("bucket")
        batch_op.drop_column("object_key")
        batch_op.drop_column("original_file_path")
        batch_op.drop_column("uploading_computer_name")
        batch_op.drop_column("kilobytes")
        batch_op.drop_column("md5")
