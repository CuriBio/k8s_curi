"""add customers table

Revision ID: 666e49886290
Revises: 49fceab10078
Create Date: 2022-04-25 11:51:39.579732

"""
import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func, text
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
        sa.Column("email", sa.String(64), nullable=False, unique=True),
        sa.Column("password", sa.String(128), nullable=False),
        sa.Column("last_login", sa.DateTime(timezone=False), server_default=func.now()),
        sa.Column("data", postgresql.JSONB, server_default="{}", nullable=True),
        sa.Column("suspended", sa.Boolean(), server_default="f", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=False), server_default=func.now(), onupdate=func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=False), nullable=True),
    )

    cb_customer_login = os.environ.get("CURIBIO_CUSTOMER_LOGIN")
    cb_customer_pw = os.environ.get("CURIBIO_CUSTOMER_PASS")

    # create curibio customer
    op.get_bind().execute(
        text("INSERT INTO customers (email, password) VALUES (:cb_customer_login, :cb_customer_pw)"),
        **{"cb_customer_login": cb_customer_login, "cb_customer_pw": cb_customer_pw},
    )
    # drop constraints on these columns individually and combine them into a single constraint
    op.drop_constraint("users_customer_id_key", "users")
    op.drop_constraint("users_name_key", "users")
    op.create_unique_constraint("users_customer_id_name_key", "users", ["name", "customer_id"])
    # drop server default of users.customer_id and make it not null
    op.alter_column("users", "customer_id", server_default=None, nullable=False)
    # put all existing users under curibio customer ID
    op.get_bind().execute(
        text(
            """
            WITH customers AS (SELECT id FROM customers WHERE email = :cb_customer_login)
            UPDATE users SET customer_id = customers.id
            FROM customers
            """
        ),
        **{"cb_customer_login": cb_customer_login},
    )

    # rename columns
    for table in ("mantarray_recording_sessions", "mantarray_session_log_files"):
        for id_type in ("customer", "user"):
            op.alter_column(
                table,
                f"{id_type}_account_id",
                new_column_name=f"{id_type}_id",
                type_=postgresql.UUID(as_uuid=True),
                postgresql_using=f"{id_type}_account_id::uuid",
            )

    # create foreign keys for tables that have customer_id column
    for table in ("users", "mantarray_recording_sessions", "mantarray_session_log_files"):
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

    op.execute("GRANT ALL PRIVILEGES ON TABLE customers TO curibio_users")
    op.execute("GRANT SELECT ON TABLE customers TO curibio_users_ro")


def downgrade():
    # revoke privileges
    # drop users_customer_id_name_key constraint
    # add users_customer_id_key constraint
    # add users_name_key constraint
    # add server default of users.customer_id and make it nullable
    # remove foreign key constraint in users, mantarray_recording_sessions, mantarray_session_log_files
    # rename columns in mantarray_recording_sessions and mantarray_session_log_files
    # revert account_type to AccountType
    # drop UserAccountType
    # drop customers table
    pass  # TODO
