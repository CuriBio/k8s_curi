"""add scope table

Revision ID: 95c63cf51c4a
Revises: 5a072ec334a3
Create Date: 2023-09-12 13:35:08.515528

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "95c63cf51c4a"
down_revision = "5a072ec334a3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "account_scopes",
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scope", sa.VARCHAR(255), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_unique_constraint(
        "account_scopes_cid_uid_scope_key", "account_scopes", ["customer_id", "user_id", "scope"]
    )

    op.execute("GRANT ALL PRIVILEGES ON TABLE account_scopes TO curibio_users")
    op.execute("GRANT SELECT ON TABLE account_scopes TO curibio_users_ro")


def downgrade():
    op.execute("REVOKE ALL PRIVILEGES ON TABLE account_scopes FROM curibio_users")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE account_scopes FROM curibio_users_ro")

    op.drop_constraint("account_scopes_cid_uid_scope_key", "account_scopes")

    op.execute("DROP TABLE account_scopes")
