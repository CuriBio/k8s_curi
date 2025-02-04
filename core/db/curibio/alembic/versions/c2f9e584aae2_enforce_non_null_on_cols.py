"""enforce non-null on cols

Revision ID: c2f9e584aae2
Revises: 309d3f752473
Create Date: 2025-02-04 13:03:34.523868

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "c2f9e584aae2"
down_revision = "309d3f752473"
branch_labels = None
depends_on = None


UPDATES = [
    ("analysis_presets", "id", "gen_random_uuid()"),  # default
    ("customers", "id", "gen_random_uuid()"),  # default
    ("customers", "data", "'{}'::jsonb"),  # default
    ("customers", "usage_restrictions", "'{}'::jsonb"),  # default
    ("customers", "previous_passwords", "'{}'::character varying[]"),  # default
    ("jobs_queue", "created_at", "now()"),  # not expecting any nulls
    ("jobs_queue", "meta", "'{}'::jsonb"),  # default
    ("jobs_result", "customer_id", "'00000000-0000-0000-0000-000000000000'"),  # not expecting any nulls
    ("jobs_result", "meta", "'{}'::jsonb"),  # default
    ("jobs_result", "type", "'mantarray'"),  # not expecting any nulls
    ("ma_controllers", "state", "'internal'"),  # default
    ("ma_main_firmware", "min_ma_controller_version", "''"),  # not expecting any nulls
    ("ma_main_firmware", "min_sting_controller_version", "''"),  # not expecting any nulls
    ("sting_controllers", "state", "'internal'"),  # default
    ("uploads", "created_at", "now()"),  # not expecting any nulls present
    ("uploads", "meta", "'{}'::jsonb"),  # default
    ("uploads", "md5", "''"),  # not expecting any nulls present
    ("uploads", "prefix", "''"),  # not expecting any nulls present
    ("uploads", "filename", "''"),  # not expecting any nulls present
    ("uploads", "type", "'mantarray'"),  # not expecting any nulls present
    ("uploads", "deleted", "'f'"),  # default
    ("uploads", "customer_id", "'00000000-0000-0000-0000-000000000000'"),  # not expecting any nulls
    ("users", "id", "gen_random_uuid()"),  # default
    ("users", "preferences", "'{}'::jsonb"),  # default
    ("users", "created_at", "now()"),  # not expecting any nulls
    ("users", "verified", "'f'"),  # default
    ("users", "previous_passwords", "'{}'::character varying[]"),  # default
]


def upgrade():
    for table, col, val in UPDATES:
        op.execute(f"UPDATE {table} SET {col}={val} WHERE {col} IS NULL")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {col} SET NOT NULL")


def downgrade():
    for table, col, _ in UPDATES:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {col} DROP NOT NULL")
