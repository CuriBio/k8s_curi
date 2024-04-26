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

FROM_CURRENT_USAGE = """
    FROM (
        SELECT ( CASE WHEN (COUNT(*) <= 2 AND COUNT(*) > 0) THEN 1 ELSE GREATEST(COUNT(*) - 1, 0) END ) AS jobs_count
        FROM jobs_result WHERE customer_id=NEW.customer_id and type=NEW.type GROUP BY upload_id
    ) dt
"""


def upgrade():
    event_broker_pass = os.getenv("EVENT_BROKER_PASS")
    if event_broker_pass is None:
        raise Exception("Missing required value for EVENT_BROKER_PASS")

    op.execute(f"CREATE USER curibio_event_broker WITH PASSWORD '{event_broker_pass}'")
    op.execute("GRANT SELECT ON TABLE account_scopes TO curibio_jobs")

    # TODO these functions should be cleaned up so there aren't so many subqueries
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION jobs_result_notify_events()
        RETURNS TRIGGER AS $$
        BEGIN
            PERFORM pg_notify(
                'events',
                (
                    json_build_object(
                        'table', 'jobs_result',
                        'username', (SELECT users.name AS username FROM users JOIN uploads ON users.id=uploads.user_id WHERE uploads.id=NEW.upload_id),
                        'user_id', (SELECT users.id FROM users JOIN uploads ON users.id=uploads.user_id WHERE uploads.id=NEW.upload_id),
                        'recipients', ARRAY(
                            SELECT DISTINCT CASE WHEN user_id IS NULL THEN customer_id ELSE user_id END
                            FROM account_scopes
                            WHERE customer_id=NEW.customer_id
                                AND (user_id=(SELECT user_id FROM uploads WHERE id=NEW.upload_id) OR scope LIKE '%admin%' OR scope=(NEW.type::text || '\\:rw_all_data'))
                        ),
                        'usage', (SELECT SUM(jobs_count) AS total_jobs {FROM_CURRENT_USAGE})
                    )::jsonb
                    || row_to_json(NEW.*)::jsonb
                )::text
            );
        RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # TODO handle deletes here?
    op.execute(
        """
        CREATE TRIGGER trig_jobs_result_notify_events
        AFTER INSERT OR UPDATE ON jobs_result
        FOR EACH ROW
        EXECUTE PROCEDURE jobs_result_notify_events();
        """
    )

    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION uploads_notify_events()
        RETURNS TRIGGER AS $$
        BEGIN
            PERFORM pg_notify(
                'events',
                (
                    json_build_object(
                        'table', 'uploads',
                        'username', (SELECT users.name AS username FROM users WHERE id=NEW.user_id),
                        'recipients', ARRAY(
                            SELECT DISTINCT CASE WHEN user_id IS NULL THEN customer_id ELSE user_id END
                            FROM account_scopes
                            WHERE customer_id=NEW.customer_id
                                AND (user_id=NEW.user_id OR scope LIKE '%admin%' OR scope=(NEW.type::text || '\\:rw_all_data'))
                        ),
                        'usage', (SELECT COUNT(*) AS total_uploads {FROM_CURRENT_USAGE})
                    )::jsonb
                    || row_to_json(NEW.*)::jsonb
                )::text
            );
        RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # TODO handle deletes here?
    op.execute(
        """
        CREATE TRIGGER trig_uploads_notify_events
        AFTER INSERT OR UPDATE ON uploads
        FOR EACH ROW
        EXECUTE PROCEDURE uploads_notify_events();
        """
    )


def downgrade():
    op.execute("REVOKE ALL PRIVILEGES ON TABLE account_scopes FROM curibio_jobs")
    op.execute("DROP USER curibio_event_broker")
    op.execute("DROP TRIGGER trig_jobs_result_notify_events ON jobs_result CASCADE")
    op.execute("DROP FUNCTION jobs_result_notify_events CASCADE")
    op.execute("DROP TRIGGER trig_uploads_notify_events ON uploads CASCADE")
    op.execute("DROP FUNCTION uploads_notify_events CASCADE")
