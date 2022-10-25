"""update UploadType and scope schema

Revision ID: da5a93c1bb08
Revises: 4aac7b465d29
Create Date: 2022-10-26 07:20:30.894705

"""
from alembic import op
import json

# revision identifiers, used by Alembic.
revision = "da5a93c1bb08"
down_revision = "4aac7b465d29"
branch_labels = None
depends_on = None


def upgrade():
    # default all existing customers and users to paid pulse3d
    op.execute(f"update users set data='{json.dumps({'scope': ['pulse3d:user:paid']})}'")
    op.execute(f"update customers set data='{json.dumps({'scope': ['pulse3d:customer:paid']})}'")

    # change mantarray uploadtype to pulse3d
    # set existing mantarray types to other accepted type that is not currently being used
    op.execute("""UPDATE uploads SET type='nautilus' WHERE type='mantarray'""")
    # rename type name to random name so existing name can be used again
    op.execute("""ALTER TYPE "UploadType" RENAME TO oldUploadType""")
    # create type with original enum values
    op.execute("""CREATE TYPE "UploadType" AS ENUM('pulse3d', 'nautilus', 'pulse2d')""")
    # set enums to column
    op.execute("""ALTER TABLE uploads ALTER COLUMN type TYPE "UploadType" USING type::text::"UploadType" """)
    # drop the old type, cleanup
    op.execute("""DROP TYPE oldUploadType""")
    op.execute("UPDATE uploads SET type='pulse3d' where type='nautilus'")


def downgrade():
    op.execute(f"update users set data='{json.dumps({'scope': ['users:free']})}'")
    op.execute(f"update customers set data='{json.dumps({'scope': ['users:admin']})}'")
    # set existing mantarray types to other accepted type that is not currently being used
    op.execute("""UPDATE uploads SET type='nautilus' WHERE type='pulse3d'""")
    # rename type name to random name so existing name can be used again
    op.execute("""ALTER TYPE "UploadType" RENAME TO oldUploadType""")
    # create type with original enum values
    op.execute("""CREATE TYPE "UploadType" AS ENUM('mantarray', 'nautilus', 'pulse2d')""")
    # set enums to column
    op.execute("""ALTER TABLE uploads ALTER COLUMN type TYPE "UploadType" USING type::text::"UploadType" """)
    # drop the old type, cleanup
    op.execute("""DROP TYPE oldUploadType""")
    op.execute("UPDATE uploads SET type='mantarray' where type='nautilus'")
