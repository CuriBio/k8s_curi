"""Add pulse3d versions table

Revision ID: 871f6d005d86
Revises: 5b1cb92fa435
Create Date: 2022-09-09 08:12:08.857420

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = "871f6d005d86"
down_revision = "5b1cb92fa435"
branch_labels = None
depends_on = None


def upgrade():
    states = ("testing", "internal", "external")

    op.create_table(
        "pulse3d_versions",
        sa.Column("version", sa.VARCHAR(15), primary_key=True),
        sa.Column("date_added", sa.DateTime(timezone=False), server_default=func.now(), nullable=False),
        sa.Column("end_of_support", sa.DateTime(timezone=False)),
        sa.Column(
            "state",
            sa.Enum(*states, name="WorkerState", create_type=True),
            server_default=states[0],
            nullable=False,
        ),
    )
    op.execute("GRANT SELECT ON TABLE pulse3d_versions TO curibio_jobs")


def downgrade():
    op.execute("REVOKE ALL PRIVILEGES ON TABLE pulse3d_versions FROM curibio_jobs")
    op.drop_table("pulse3d_versions")
    op.execute('DROP TYPE "WorkerState"')
