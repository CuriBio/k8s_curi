"""add grafana ro user

Revision ID: 2acde568c771
Revises: 4ed3b25ebd9c
Create Date: 2024-01-11 11:12:10.028344

"""
from alembic import op
import sqlalchemy as sa
import os


# revision identifiers, used by Alembic.
revision = "2acde568c771"
down_revision = "4ed3b25ebd9c"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(f"CREATE USER grafana_ro WITH PASSWORD '{os.getenv('GRAFANA_PASS_RO')}'")

    for table in ("uploads", "jobs_result", "users", "customers", "account_scopes"):
        op.execute(f"GRANT SELECT ON TABLE {table} TO grafana_ro")


def downgrade():
    for table in ("uploads", "jobs_result", "users", "customers", "account_scopes"):
        op.execute(f"REVOKE ALL PRIVILEGES ON TABLE {table} FROM grafana_ro")

    op.execute("DROP USER grafana_ro")
