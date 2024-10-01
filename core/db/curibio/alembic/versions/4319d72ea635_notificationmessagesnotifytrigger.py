"""NotificationMessagesNotifyTrigger

Revision ID: 4319d72ea635
Revises: a869e370f0c7
Create Date: 2024-10-01 12:11:07.904287

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "4319d72ea635"
down_revision = "a869e370f0c7"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE OR REPLACE FUNCTION notification_messages_notify()
        RETURNS TRIGGER AS $$
        BEGIN
            PERFORM pg_notify(
                'events',
                (
                    json_build_object(
                        'table', 'notification_messages',
                        'subject', (SELECT subject FROM notifications WHERE notifications.id=NEW.notification_id),
                        'body', (SELECT body FROM notifications WHERE notifications.id=NEW.notification_id)
                    )::jsonb
                    || (row_to_json(NEW.*)::jsonb)
                )::text
            );
        RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER notification_messages_notify_trigger
        AFTER INSERT ON notification_messages
        FOR EACH ROW
        EXECUTE PROCEDURE notification_messages_notify();
        """
    )


def downgrade():
    op.execute("DROP TRIGGER notification_messages_notify_trigger ON notification_messages CASCADE")
    op.execute("DROP FUNCTION notification_messages_notify CASCADE")
