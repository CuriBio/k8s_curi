"""addOrganizationAndAdminOrgIdToCustomers

Revision ID: 90ec0862fdde
Revises: 1fb818f900b6
Create Date: 2024-06-14 10:16:47.032714

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "90ec0862fdde"
down_revision = "1fb818f900b6"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE customers ADD COLUMN sso_organization VARCHAR(256)")
    op.execute("ALTER TABLE customers ADD COLUMN sso_admin_org_id VARCHAR(256)")
    op.execute(
        "ALTER TABLE customers ADD CONSTRAINT customers_sso_organization_key UNIQUE (sso_organization)"
    )
    op.execute(
        "ALTER TABLE customers ADD CONSTRAINT customers_sso_admin_org_id_key UNIQUE (sso_admin_org_id)"
    )


def downgrade():
    op.execute("ALTER TABLE customers DROP CONSTRAINT customers_sso_admin_org_id_key")
    op.execute("ALTER TABLE customers DROP CONSTRAINT customers_sso_organization_key")
    op.execute("ALTER TABLE customers DROP COLUMN sso_admin_org_id")
    op.execute("ALTER TABLE customers DROP COLUMN sso_organization")
