"""createNotificationMessagesTable

Revision ID: a869e370f0c7
Revises: 7c167985704d
Create Date: 2024-09-16 11:01:35.451970

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = "a869e370f0c7"
down_revision = "7c167985704d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notification_messages",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now(), nullable=False),
        sa.Column("notification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"], ondelete="CASCADE"),
    )

    op.execute("GRANT SELECT ON TABLE notification_messages TO curibio_jobs_ro")
    op.execute("GRANT ALL PRIVILEGES ON TABLE notification_messages TO curibio_jobs")


def downgrade():
    op.execute("REVOKE ALL PRIVILEGES ON TABLE notification_messages FROM curibio_jobs")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE notification_messages FROM curibio_jobs_ro")

    op.drop_table("notification_messages")
