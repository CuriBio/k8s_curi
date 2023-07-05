"""disallow previous 5 passwords

Revision ID: 953c09a70adb
Revises: 528cbf8884aa
Create Date: 2023-07-03 11:34:08.104239

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "953c09a70adb"
down_revision = "528cbf8884aa"
branch_labels = None
depends_on = None


def upgrade():
    # for table in ("users", "customers"):
    #     op.execute(f"ALTER TABLE {table} ADD COLUMN previous_passwords VARCHAR(128)[5]")
    #     op.execute(f"UPDATE {table} SET previous_passwords[0]=password WHERE password IS NOT null")
    # also add reset token column in place of link column
    op.alter_column("customers", "pw_reset_link", new_column_name="reset_token")
    op.alter_column("users", "pw_reset_verify_link", new_column_name="reset_token")


def downgrade():
    for table in ("users", "customers"):
        op.drop_column(table, "previous_passwords")

    op.alter_column("customers", "reset_token", new_column_name="pw_reset_link")
    op.alter_column("users", "reset_token", new_column_name="pw_reset_verify_link")
