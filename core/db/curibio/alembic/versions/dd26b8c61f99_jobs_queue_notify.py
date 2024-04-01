"""jobs_queue notify

Revision ID: dd26b8c61f99
Revises: c8d1b4377985
Create Date: 2024-04-01 14:45:29.146796

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "dd26b8c61f99"
down_revision = "c8d1b4377985"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE OR REPLACE FUNCTION notify_jobs_queue()
        RETURNS TRIGGER AS $$
        BEGIN
            SELECT pg_notify('jobs_queue', '');
        RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trig_notify_jobs_queue
        AFTER INSERT ON jobs_queue
        FOR EACH ROW
        EXECUTE PROCEDURE notify_jobs_queue();
        """
    )


def downgrade():
    op.execute("DROP TRIGGER trig_notify_jobs_queue ON jobs_queue CASCADE")
    op.execute("DROP FUNCTION notify_jobs_queue CASCADE")
