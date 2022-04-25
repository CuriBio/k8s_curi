"""add customers table

Revision ID: 666e49886290
Revises: 49fceab10078
Create Date: 2022-04-25 11:51:39.579732

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "666e49886290"
down_revision = "49fceab10078"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "customers",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), unique=True
        ),
        sa.Column("name", sa.String(32), nullable=False, unique=True),
        sa.Column("email", sa.String(64), nullable=False, unique=True),
        sa.Column("password", sa.String(128), nullable=False),
        sa.Column("last_login", sa.DateTime(timezone=False), server_default=func.now()),
        sa.Column("data", postgresql.JSONB, server_default="{}", nullable=True),
        sa.Column("suspended", sa.Boolean(), server_default="f", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=False), server_default=func.now(), onupdate=func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=False), nullable=True),
    )

    for table in ("users", "mantarray_recording_sessions", "mantarray_session_log_files"):
        if table != "users":
            op.alter_column(
                table,
                "customer_account_id",
                new_column_name="customer_id",
                type_=postgresql.UUID(as_uuid=True),
                postgresql_using="customer_account_id::uuid",
            )
        op.create_foreign_key(f"fk_{table}_customers", table, "customers", ["customer_id"], ["id"])

    # convert any admin users to free users
    op.execute("UPDATE users SET account_type = 'free' WHERE account_type = 'admin'")
    # update type
    new_account_type = sa.Enum("free", "paid", name="UserAccountType", create_type=True)
    new_account_type.create(op.get_bind(), checkfirst=False)
    op.alter_column(
        "users",
        "account_type",
        type_=new_account_type,
        postgresql_using='account_type::text::"UserAccountType"',
    )
    # drop old type
    old_account_type = sa.Enum("free", "paid", "admin", name="AccountType", create_type=True)
    old_account_type.drop(op.get_bind(), checkfirst=False)


def downgrade():
    pass  # TODO
