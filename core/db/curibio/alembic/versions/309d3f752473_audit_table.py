"""audit table

Revision ID: 309d3f752473
Revises: 6b689a41f489
Create Date: 2024-11-12 13:01:19.060977

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "309d3f752473"
down_revision = "6b689a41f489"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SCHEMA audit")
    op.execute("REVOKE CREATE ON SCHEMA audit FROM public")
    op.execute(
        """
        CREATE TABLE audit.logged_actions (
            schema_name   TEXT NOT NULL,
            table_name    TEXT NOT NULL,
            user_name     TEXT,
            timestamp     TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            action        TEXT NOT NULL CHECK (action IN ('I','D','U')),
            original_data JSONB,
            new_data      JSONB,
            query         TEXT
        ) WITH (fillfactor=100)
        """
    )
    op.execute("CREATE INDEX audit_log_table_idx ON audit.logged_actions(table_name)")
    op.execute("CREATE INDEX audit_log_timestamp_idx ON audit.logged_actions(timestamp)")
    op.execute("CREATE INDEX audit_log_action_idx ON audit.logged_actions(action)")

    op.execute(
        """
            CREATE OR REPLACE FUNCTION audit.log_action() RETURNS trigger AS $body$
            DECLARE
                v_old_data JSONB;
                v_new_data JSONB;
            BEGIN
                if (TG_OP = 'UPDATE') then
                    v_old_data := row_to_json(OLD.*)::jsonb;
                    v_new_data := row_to_json(NEW.*)::jsonb;
                    insert into audit.logged_actions (schema_name, table_name, user_name, action, original_data, new_data ,query)
                    values (TG_TABLE_SCHEMA::TEXT, TG_TABLE_NAME::TEXT, session_user::TEXT, substring(TG_OP,1,1), v_old_data, v_new_data, current_query());
                    RETURN NEW;
                elsif (TG_OP = 'DELETE') then
                    v_old_data := row_to_json(OLD.*)::jsonb;
                    insert into audit.logged_actions (schema_name, table_name, user_name, action, original_data, query)
                    values (TG_TABLE_SCHEMA::TEXT, TG_TABLE_NAME::TEXT, session_user::TEXT, substring(TG_OP,1,1), v_old_data, current_query());
                    RETURN OLD;
                elsif (TG_OP = 'INSERT') then
                    v_new_data := row_to_json(NEW.*)::jsonb;
                    insert into audit.logged_actions (schema_name, table_name, user_name, action, new_data, query)
                    values (TG_TABLE_SCHEMA::TEXT, TG_TABLE_NAME::TEXT, session_user::TEXT, substring(TG_OP,1,1), v_new_data, current_query());
                    RETURN NEW;
                else
                    RAISE WARNING '[AUDIT.LOG_ACTION] - Other action occurred: %, at %',TG_OP,now();
                    RETURN NULL;
                end if;

            EXCEPTION
                WHEN data_exception THEN
                    RAISE WARNING '[AUDIT.LOG_ACTION] - UDF ERROR [DATA EXCEPTION] - SQLSTATE: %, SQLERRM: %',SQLSTATE,SQLERRM;
                    RETURN NULL;
                WHEN unique_violation THEN
                    RAISE WARNING '[AUDIT.LOG_ACTION] - UDF ERROR [UNIQUE] - SQLSTATE: %, SQLERRM: %',SQLSTATE,SQLERRM;
                    RETURN NULL;
                WHEN others THEN
                    RAISE WARNING '[AUDIT.LOG_ACTION] - UDF ERROR [OTHER] - SQLSTATE: %, SQLERRM: %',SQLSTATE,SQLERRM;
                    RETURN NULL;
            END;
            $body$
            LANGUAGE plpgsql
            SECURITY DEFINER
            SET search_path = pg_catalog, audit
        """
    )

    for table in (
        "account_scopes",
        "advanced_analysis_result",
        "advanced_analysis_versions",
        "alembic_version",
        "analysis_presets",
        "customers",
        "jobs_queue",
        "jobs_result",
        "ma_channel_firmware",
        "ma_controllers",
        "ma_main_firmware",
        "mantarray_recording_sessions",
        "mantarray_session_log_files",
        "maunits",
        "notification_messages",
        "notifications",
        "pulse3d_versions",
        "sting_controllers",
        "uploads",
        "users",
    ):
        op.execute(
            f"""
            CREATE TRIGGER {table}_audit
            AFTER INSERT OR UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE PROCEDURE audit.log_action();
            """
        )

    op.execute("GRANT SELECT ON audit.logged_actions TO grafana_ro")


def downgrade():
    op.execute("REVOKE ALL PRIVILEGES ON TABLE audit.logged_actions FROM grafana_ro")
    op.execute("DROP SCHEMA audit CASCADE")
