"""add customers table

Revision ID: 666e49886290
Revises: 49fceab10078
Create Date: 2022-04-25 11:51:39.579732

"""
import os

from alembic import op
from argon2 import PasswordHasher
import sqlalchemy as sa
from sqlalchemy.sql import func, text
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "666e49886290"
down_revision = "49fceab10078"
branch_labels = None
depends_on = None

# TODO move default value of jobs_result.finished_at to jobs_result.created_at


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
    cb_customer_pw_hash = PasswordHasher().hash(os.environ.get("CURIBIO_CUSTOMER_PASS"))

    # create curibio customer
    op.get_bind().execute(
        text("INSERT INTO customers (email, password) VALUES (:cb_customer_login, :cb_customer_pw)"),
        **{"cb_customer_login": cb_customer_login, "cb_customer_pw": cb_customer_pw_hash},
    )
    # drop constraints on these columns individually and combine them into a single unique constraint
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

    # rename columns relevant tables
    for table in ("mantarray_recording_sessions", "mantarray_session_log_files"):
        for id_type in ("customer", "user"):
            op.alter_column(
                table,
                f"{id_type}_account_id",
                new_column_name=f"{id_type}_id",
                type_=postgresql.UUID(as_uuid=True),
                postgresql_using=f"{id_type}_account_id::uuid",
            )

    # create foreign key contraints for tables that have customer_id column
    for table in ("users", "mantarray_recording_sessions", "mantarray_session_log_files"):
        op.create_foreign_key(f"fk_{table}_customers", table, "customers", ["customer_id"], ["id"])

    # convert any admin users to free users
    op.execute("UPDATE users SET account_type = 'free' WHERE account_type = 'admin'")
    # update account_type
    new_account_type = sa.Enum("free", "paid", name="UserAccountType", create_type=True)
    new_account_type.create(op.get_bind(), checkfirst=False)
    op.alter_column(
        "users",
        "account_type",
        type_=new_account_type,
        postgresql_using='account_type::text::"UserAccountType"',
    )
    # drop old account_type
    old_account_type = sa.Enum("free", "paid", "admin", name="AccountType", create_type=True)
    old_account_type.drop(op.get_bind(), checkfirst=False)

    op.execute("GRANT ALL PRIVILEGES ON TABLE customers TO curibio_users")
    op.execute("GRANT SELECT ON TABLE customers TO curibio_users_ro")


def downgrade():
    # revoke privileges
    op.execute("REVOKE ALL PRIVILEGES ON TABLE customers FROM curibio_users")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE customers FROM curibio_users_ro")

    # remove foreign key constraint in users, mantarray_recording_sessions, mantarray_session_log_files
    for table in ("users", "mantarray_recording_sessions", "mantarray_session_log_files"):
        op.drop_constraint(f"fk_{table}_customers", table)

    # drop combined unique constraint
    op.drop_constraint("users_customer_id_name_key", "users")
    # since all customer IDs will need to be unique for users, need to give them all random UUIDs before adding constraint
    op.execute("UPDATE users SET customer_id = gen_random_uuid()")
    # re-add individual unique constraints
    op.create_unique_constraint("users_customer_id_key", "users", ["customer_id"])
    op.create_unique_constraint("users_name_key", "users", ["name"])
    # add server default of users.customer_id and make it nullable
    op.alter_column("users", "customer_id", server_default=sa.text("gen_random_uuid()"), nullable=True)

    # rename columns
    for table in ("mantarray_recording_sessions", "mantarray_session_log_files"):
        for id_type in ("customer", "user"):
            op.alter_column(
                table,
                f"{id_type}_id",
                new_column_name=f"{id_type}_account_id",
                type_=sa.VARCHAR(255),
            )

    # revert account_type back to AccountType
    new_account_type = sa.Enum("free", "paid", "admin", name="AccountType", create_type=True)
    new_account_type.create(op.get_bind(), checkfirst=False)
    op.alter_column(
        "users",
        "account_type",
        type_=new_account_type,
        postgresql_using='account_type::text::"AccountType"',
    )
    # drop UserAccountType
    old_account_type = sa.Enum("free", "paid", name="UserAccountType", create_type=True)
    old_account_type.drop(op.get_bind(), checkfirst=False)

    # drop customers table
    op.execute("DROP TABLE customers")
