"""remove metadata from notify payloads

Revision ID: 9566734eccae
Revises: ba1300aff257
Create Date: 2024-08-02 15:47:57.797403

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "9566734eccae"
down_revision = "ba1300aff257"
branch_labels = None
depends_on = None


FROM_CURRENT_USAGE = """
    FROM (
        SELECT ( CASE WHEN (COUNT(*) <= 2 AND COUNT(*) > 0) THEN 1 ELSE GREATEST(COUNT(*) - 1, 0) END ) AS jobs_count
        FROM jobs_result WHERE customer_id=NEW.customer_id and type=NEW.type GROUP BY upload_id
    ) dt
"""


def upgrade():
    # TODO these functions should be cleaned up so there aren't so many subqueries
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
                    || (row_to_json(NEW.*)::jsonb - 'meta')
                )::text
            );
        RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

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
                    || (row_to_json(NEW.*)::jsonb - 'meta')
                )::text
            );
        RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def downgrade():
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
