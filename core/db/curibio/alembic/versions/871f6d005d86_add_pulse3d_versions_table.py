"""Add pulse3d versions table, fix updated_at trigger

Revision ID: 871f6d005d86
Revises: 5b1cb92fa435
Create Date: 2022-09-09 08:12:08.857420

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = "871f6d005d86"
down_revision = "5b1cb92fa435"
branch_labels = None
depends_on = None


def upgrade():
    states = ("testing", "internal", "external", "deprecated")

    op.create_table(
        "pulse3d_versions",
        sa.Column("version", sa.VARCHAR(15), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), server_default=func.now(), nullable=False),
        sa.Column(
            "state",
            sa.Enum(*states, name="WorkerState", create_type=True),
            server_default=states[0],
            nullable=False,
        ),
    )
    op.execute("GRANT SELECT ON TABLE pulse3d_versions TO curibio_jobs")

    # add update function
    op.execute(
        """
        CREATE OR REPLACE FUNCTION trigger_set_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # create trigger to call update function, add to all tables with an 'updated_at' column
    for table in ("customers", "users", "uploads", "pulse3d_versions"):
        op.execute(
            f"""
            CREATE TRIGGER set_timestamp
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE PROCEDURE trigger_set_timestamp();
            """
        )


def downgrade():
    op.execute("REVOKE ALL PRIVILEGES ON TABLE pulse3d_versions FROM curibio_jobs")
    op.drop_table("pulse3d_versions")
    op.execute('DROP TYPE "WorkerState"')
    op.execute("DROP FUNCTION trigger_set_timestamp() CASCADE")
