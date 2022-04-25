"""create users table

Revision ID: be5bfe07156a
Revises: 
Create Date: 2022-03-12 13:50:27.312532

"""
import os
from alembic import op
from sqlalchemy.sql import func
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "be5bfe07156a"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), unique=True
        ),
        sa.Column("name", sa.String(32), nullable=False, unique=True),
        sa.Column("email", sa.String(64), nullable=False, unique=True),
        sa.Column("password", sa.String(128), nullable=False),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            unique=True,
        ),
        sa.Column(
            "account_type",
            sa.Enum("free", "paid", "admin", name="AccountType", create_type=True),
            nullable=False,
        ),
        sa.Column("last_login", sa.DateTime(timezone=False), server_default=func.now()),
        sa.Column("data", postgresql.JSONB, server_default="{}", nullable=True),
        sa.Column("suspended", sa.Boolean(), server_default="f", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=False), server_default=func.now(), onupdate=func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=False), nullable=True),
    )

    env_vars = {}
    for env_var_name in ("TABLE_USER_PASS", "TABLE_USER_PASS_RO"):
        env_var = os.getenv(env_var_name)
        if env_var is None:
            raise Exception(f"Missing required value for {env_var_name}")
        env_vars[env_var_name] = env_var

    op.execute(f"CREATE USER curibio_users WITH PASSWORD '{env_vars['TABLE_USER_PASS']}'")
    op.execute(f"CREATE USER curibio_users_ro WITH PASSWORD '{env_vars['TABLE_USER_PASS_RO']}'")

    op.execute("GRANT ALL PRIVILEGES ON TABLE users TO curibio_users")
    op.execute("GRANT SELECT ON TABLE users TO curibio_users_ro")


def downgrade():
    op.execute("REVOKE ALL PRIVILEGES ON TABLE users FROM curibio_users")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE users FROM curibio_users_ro")

    op.execute("DROP USER curibio_users")
    op.execute("DROP USER curibio_users_ro")

    op.execute("DROP TABLE users CASCADE")
    op.execute('DROP TYPE "AccountType"')
