"""update pulse3d scopes to mantarray

Revision ID: 35e6c6b7ec8e
Revises: 95c63cf51c4a
Create Date: 2023-09-26 08:46:32.666101

"""
from alembic import op
import sqlalchemy as sa
import json

# revision identifiers, used by Alembic.
revision = "35e6c6b7ec8e"
down_revision = "95c63cf51c4a"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE account_scopes SET scope=REPLACE(scope, 'pulse3d','mantarray')")
    op.execute(
        f"UPDATE customers SET data=NULL, usage_restrictions='{json.dumps({'mantarray': {'jobs': -1, 'uploads': -1, 'expiration_date': None}, 'nautilus': {'jobs': -1, 'uploads': -1, 'expiration_date': None}})}'"
    )
    op.execute("UPDATE users SET data=NULL")

    # change pulse3d uploadtype to mantarray
    op.execute("UPDATE uploads SET type='nautilus' WHERE type='pulse3d'")
    op.execute("UPDATE jobs_result SET type='nautilus' WHERE type='pulse3d'")
    op.execute("ALTER TABLE jobs_result ALTER COLUMN type DROP DEFAULT")

    # rename type name to random name so existing name can be used again
    op.execute("""ALTER TYPE "UploadType" RENAME TO oldUploadType""")
    # create type with original enum values
    op.execute("""CREATE TYPE "UploadType" AS ENUM('mantarray', 'nautilus', 'pulse2d')""")
    # set enums to column
    op.execute("""ALTER TABLE uploads ALTER COLUMN type TYPE "UploadType" USING type::text::"UploadType" """)
    op.execute(
        """ALTER TABLE jobs_result ALTER COLUMN type TYPE "UploadType" USING type::text::"UploadType" """
    )

    # drop the old type, cleanup
    op.execute("DROP TYPE oldUploadType")
    op.execute("UPDATE uploads SET type='mantarray' where type='nautilus'")
    op.execute("UPDATE jobs_result SET type='mantarray' where type='nautilus'")
    op.execute("ALTER TABLE jobs_result ALTER COLUMN type SET DEFAULT 'mantarray'")

    # drop account_type column from customers, no longer needed since we have multiple products with independent tiers
    # this info can be found in the usage_restrictions column and account_scopes table
    op.drop_column("users", "account_type")


def downgrade():
    op.execute(
        " UPDATE account_scopes SET scope = REPLACE(scope, 'mantarray','pulse3d') where scope not in ('mantarray:firmware:get', 'mantarray:serial_number:edit')"
    )
    # will be missing certain scopes that were dropped in upgrade function, this will presume most functionality
    op.execute(
        f"UPDATE customers set data='{json.dumps({'scope': ['pulse3d:paid']})}', usage_restrictions='{json.dumps({'pulse3d': {'jobs': -1, 'uploads': -1, 'expiration_date': None}})}'"
    )
    op.execute(f"UPDATE users set data='{json.dumps({'scope': ['pulse3d:paid']})}'")

    # set existing mantarray types to other accepted type that is not currently being used
    op.execute("UPDATE uploads SET type='nautilus' WHERE type='mantarray'")
    op.execute("UPDATE jobs_result SET type='nautilus' WHERE type='mantarray'")
    op.execute("ALTER TABLE jobs_result ALTER COLUMN type DROP DEFAULT")

    # rename type name to random name so existing name can be used again
    op.execute("""ALTER TYPE "UploadType" RENAME TO oldUploadType""")
    # create type with original enum values
    op.execute("""CREATE TYPE "UploadType" AS ENUM('pulse3d', 'nautilus', 'pulse2d')""")
    # set enums to column
    op.execute("""ALTER TABLE uploads ALTER COLUMN type TYPE "UploadType" USING type::text::"UploadType" """)
    op.execute(
        """ALTER TABLE jobs_result ALTER COLUMN type TYPE "UploadType" USING type::text::"UploadType" """
    )

    # drop the old type, cleanup
    op.execute("DROP TYPE oldUploadType")
    op.execute("UPDATE uploads SET type='pulse3d' where type='nautilus'")
    op.execute("UPDATE jobs_result SET type='pulse3d' where type='nautilus'")
    op.execute("ALTER TABLE jobs_result ALTER COLUMN type SET DEFAULT 'pulse3d'")

    op.add_column(
        "users",
        sa.Column(
            "account_type",
            sa.Enum("free", "paid", "admin", name="UserAccountType", create_type=True),
            nullable=False,
            server_default="paid",
        ),
    )
