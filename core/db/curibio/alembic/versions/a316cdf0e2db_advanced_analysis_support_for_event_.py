"""advanced analysis support for event broker

Revision ID: a316cdf0e2db
Revises: 6769347ee5c7
Create Date: 2024-08-29 12:41:27.211210

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "a316cdf0e2db"
down_revision = "6769347ee5c7"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("GRANT SELECT ON TABLE advanced_analysis_versions TO curibio_event_broker")

    # TODO these functions should be cleaned up so there aren't so many subqueries
    op.execute(
        """
        CREATE OR REPLACE FUNCTION advanced_analysis_result_notify_events()
        RETURNS TRIGGER AS $$
        BEGIN
            PERFORM pg_notify(
                'events',
                (
                    json_build_object(
                        'table', 'advanced_analysis_result',
                        'username', (SELECT users.name AS username FROM users WHERE users.id=NEW.user_id),
                        'recipients', ARRAY(
                            SELECT DISTINCT CASE WHEN user_id IS NULL THEN customer_id ELSE user_id END
                            FROM account_scopes
                            WHERE customer_id=NEW.customer_id
                                AND (user_id=NEW.user_id OR scope LIKE '%admin%' OR scope='advanced_analysis\\:rw_all_data')
                        ),
                        'usage', (SELECT COUNT(*) FROM advanced_analysis_versions WHERE customer_id=NEW.customer_id)
                    )::jsonb
                    || (row_to_json(NEW.*)::jsonb - 'meta')
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
        CREATE TRIGGER trig_advanced_analysis_result_notify_events
        AFTER INSERT OR UPDATE ON jobs_result
        FOR EACH ROW
        EXECUTE PROCEDURE jobs_result_notify_events();
        """
    )


def downgrade():
    op.execute("REVOKE ALL PRIVILEGES ON TABLE advanced_analysis_versions FROM curibio_event_broker")

    op.execute("DROP TRIGGER trig_advanced_analysis_result_notify_events ON jobs_result CASCADE")
    op.execute("DROP FUNCTION advanced_analysis_result_notify_events CASCADE")
