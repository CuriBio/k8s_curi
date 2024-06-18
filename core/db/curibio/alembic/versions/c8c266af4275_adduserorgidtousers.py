"""addUserOrgIdToUsers

Revision ID: c8c266af4275
Revises: 90ec0862fdde
Create Date: 2024-06-17 15:27:38.030964

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "c8c266af4275"
down_revision = "90ec0862fdde"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE users ADD COLUMN sso_user_org_id VARCHAR(256)")
    op.execute("ALTER TABLE users ADD CONSTRAINT users_sso_user_org_id_key UNIQUE (sso_user_org_id)")


def downgrade():
    op.execute("ALTER TABLE users DROP CONSTRAINT users_sso_user_org_id_key")
    op.execute("ALTER TABLE users DROP COLUMN sso_user_org_id")
