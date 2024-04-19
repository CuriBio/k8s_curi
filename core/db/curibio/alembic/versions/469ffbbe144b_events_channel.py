"""events channel

Revision ID: 469ffbbe144b
Revises: 848fb69a8766
Create Date: 2024-04-19 12:40:45.294650

"""

import os
from alembic import op


# revision identifiers, used by Alembic.
revision = "469ffbbe144b"
down_revision = "848fb69a8766"
branch_labels = None
depends_on = None


TABLES = ("jobs_result", "uploads")


SELECT_RECIPIENTS = """
    SELECT DISTINCT CASE WHEN user_id IS NULL THEN customer_id ELSE user_id END
    FROM account_scopes
    WHERE customer_id=(SELECT customer_id FROM users WHERE id=NEW.user_id)
        AND (user_id=NEW.user_id OR scope LIKE '%admin%' OR scope=(NEW.type::text || '\\:rw_all_data'))
"""


def upgrade():
    event_broker_pass = os.getenv("EVENT_BROKER_PASS")
    if event_broker_pass is None:
        raise Exception("Missing required value for EVENT_BROKER_PASS")
    op.execute(f"CREATE USER curibio_event_broker WITH PASSWORD '{event_broker_pass}'")

    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION notify_events()
        RETURNS TRIGGER AS $$
        BEGIN
            PERFORM pg_notify(
                'events',
                (
                    json_build_object(
                        'table', TG_ARGV[0],
                        'recipients', ARRAY({SELECT_RECIPIENTS})
                    )::jsonb
                    || row_to_json(NEW.*)::jsonb
                )::text
            );
        RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in TABLES:
        # TODO handle deletes here?
        op.execute(
            f"""
            CREATE TRIGGER trig_notify_events
            AFTER INSERT OR UPDATE ON {table}
            FOR EACH ROW
            EXECUTE PROCEDURE notify_events('{table}');
            """
        )


def downgrade():
    op.execute("DROP USER curibio_event_broker")
    for table in TABLES:
        op.execute(f"DROP TRIGGER trig_notify_events ON {table} CASCADE")
    op.execute("DROP FUNCTION notify_events CASCADE")
