"""createNotificationsTable

Revision ID: 6610b7f75d43
Revises: ea52b286a184
Create Date: 2024-08-27 08:15:40.414670

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = "6610b7f75d43"
down_revision = "ea52b286a184"
branch_labels = None
depends_on = None
notification_types = ("customers_and_users", "customers", "users")


def upgrade():
    op.create_table(
        "notifications",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now(), nullable=False),
        sa.Column("subject", sa.String(128), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "notification_type",
            sa.Enum(*notification_types, name="NotificationType", create_type=True),
            server_default=notification_types[0],
            nullable=False,
        ),
    )

    op.execute("GRANT ALL PRIVILEGES ON TABLE notifications TO curibio_jobs")
    op.execute("GRANT SELECT ON TABLE notifications TO curibio_jobs_ro")


def downgrade():
    op.execute("REVOKE ALL PRIVILEGES ON TABLE notifications FROM curibio_jobs")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE notifications FROM curibio_jobs_ro")

    op.drop_table("notifications")

    op.execute('DROP TYPE "NotificationType" CASCADE')
