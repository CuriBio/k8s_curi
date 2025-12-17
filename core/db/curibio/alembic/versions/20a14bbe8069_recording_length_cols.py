"""recording length cols

Revision ID: 20a14bbe8069
Revises: e6e3b358784c
Create Date: 2025-11-18 13:31:29.664756

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20a14bbe8069"
down_revision = "e6e3b358784c"
branch_labels = None
depends_on = None

TABLES = ("uploads", "jobs_result")


def upgrade():
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ADD COLUMN recording_length_seconds double precision")
    op.execute("UPDATE uploads SET recording_length_seconds=(meta->>'full_recording_length')::float")
    op.execute(
        "UPDATE jobs_result SET recording_length_seconds=((meta->>'recording_length_ms')::float / (CASE WHEN meta->>'version' like '0%' THEN 1e6 ELSE 1 END))"
    )


def downgrade():
    for table in TABLES:
        op.drop_column(table, "recording_length_seconds")
