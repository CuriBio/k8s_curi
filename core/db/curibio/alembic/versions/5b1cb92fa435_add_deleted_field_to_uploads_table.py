"""add deleted field to uploads table

Revision ID: 5b1cb92fa435
Revises: 3a2553a6d4b2
Create Date: 2022-08-14 18:57:08.221580

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5b1cb92fa435"
down_revision = "3a2553a6d4b2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("uploads", sa.Column("deleted", sa.Boolean(), server_default="f"))
    op.execute("""ALTER TYPE "JobStatus" ADD VALUE 'deleted'""")


def downgrade():
    op.drop_column("uploads", "deleted")
    # set existing deleted statuses to an old status: error for now?
    op.execute("""UPDATE jobs_result SET status='error' WHERE status='deleted'""")
    # rename type name to random name so existing name can be used again
    op.execute("""ALTER TYPE "JobStatus" RENAME TO oldJobStatus""")
    # create type with original enum values
    op.execute("""CREATE TYPE "JobStatus" AS ENUM('pending', 'error', 'finished')""")
    # set enums to column
    op.execute(
        """ALTER TABLE jobs_result ALTER COLUMN status TYPE "JobStatus" USING status::text::"JobStatus" """
    )
    # drop the old type, cleanup
    op.execute("""DROP TYPE oldJobStatus""")
