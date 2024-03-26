"""update upload types

Revision ID: 0c8fe377c814
Revises: abc8d3935c1b
Create Date: 2024-01-24 13:35:03.951300

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "0c8fe377c814"
down_revision = "abc8d3935c1b"
branch_labels = None
depends_on = None


def upgrade():
    # setting to pulse2d since it isn't assigned anywhere yet
    op.execute("UPDATE jobs_result SET type='pulse2d' WHERE type='nautilus'")
    op.execute("UPDATE uploads SET type='pulse2d' WHERE type='nautilus'")
    op.execute("ALTER TABLE jobs_result ALTER COLUMN type DROP DEFAULT")

    # rename type name to random name so existing name can be used again
    op.execute("""ALTER TYPE "UploadType" RENAME TO oldUploadType""")
    # create type with original enum values
    op.execute("""CREATE TYPE "UploadType" AS ENUM('mantarray', 'nautilai', 'pulse2d')""")
    # set enums to column
    op.execute("""ALTER TABLE uploads ALTER COLUMN type TYPE "UploadType" USING type::text::"UploadType" """)
    op.execute(
        """ALTER TABLE jobs_result ALTER COLUMN type TYPE "UploadType" USING type::text::"UploadType" """
    )

    # drop the old type, cleanup
    op.execute("DROP TYPE oldUploadType")
    op.execute("UPDATE jobs_result SET type='nautilai' where type='pulse2d'")
    op.execute("UPDATE uploads SET type='nautilai' where type='pulse2d'")


def downgrade():
    # set existing mantarray types to other accepted type that is not currently being used
    op.execute("UPDATE jobs_result SET type='pulse2d' WHERE type='nautilai'")
    op.execute("UPDATE uploads SET type='pulse2d' WHERE type='nautilai'")
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
    op.execute("UPDATE jobs_result SET type='nautilus' where type='pulse2d'")
    op.execute("UPDATE uploads SET type='nautilus' where type='pulse2d'")
