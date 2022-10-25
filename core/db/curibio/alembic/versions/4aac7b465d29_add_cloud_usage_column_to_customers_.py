"""add cloud usage column to customers table

Revision ID: 4aac7b465d29
Revises: 705b8a7903c8
Create Date: 2022-10-19 10:39:53.261901

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision = "4aac7b465d29"
down_revision = "705b8a7903c8"
branch_labels = None
depends_on = None


def upgrade():

    op.add_column("customers", sa.Column("usage_restrictions", pg.JSONB, server_default="{}", nullable=True))
    op.add_column(
        "jobs_result",
        sa.Column(  # keeping old types here, will update to pulse3d type in next migration
            "type",
            sa.Enum("mantarray", "nautilus", "pulse2d", name="UploadType"),
            nullable=True,
            server_default="mantarray",
        ),
    )

    # create foreign key contraints for tables that have customer_id column
    for table in ("uploads", "jobs_result"):
        op.add_column(table, sa.Column("customer_id", pg.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(f"fk_{table}_customers", table, "customers", ["customer_id"], ["id"])

    op.execute(
        "UPDATE uploads SET customer_id=(SELECT customer_id from users where uploads.user_id=users.id)"
    )
    op.execute(
        "UPDATE jobs_result SET customer_id=(SELECT customer_id from uploads where jobs_result.upload_id=uploads.id)"
    )


def downgrade():
    op.drop_column("customers", "usage_restrictions")
    op.drop_column("jobs_result", "type")

    # remove foreign key constraint in users, mantarray_recording_sessions, mantarray_session_log_files
    for table in ("uploads", "jobs_result"):
        op.drop_constraint(f"fk_{table}_customers", table)
        op.drop_column(table, "customer_id")
