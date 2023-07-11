"""add analysis presets table

Revision ID: c3ab9e9629ce
Revises: 953c09a70adb
Create Date: 2023-07-04 08:40:06.542894

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "c3ab9e9629ce"
down_revision = "953c09a70adb"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "analysis_presets",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), unique=True
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.VARCHAR(255), nullable=False),
        sa.Column("parameters", postgresql.JSONB, server_default="{}", nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.execute("GRANT ALL PRIVILEGES ON TABLE analysis_presets TO curibio_jobs")
    op.execute("GRANT SELECT ON TABLE analysis_presets TO curibio_jobs_ro")


def downgrade():
    op.execute("REVOKE ALL PRIVILEGES ON TABLE analysis_presets FROM curibio_jobs")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE analysis_presets FROM curibio_jobs_ro")
    op.drop_table("analysis_presets")
