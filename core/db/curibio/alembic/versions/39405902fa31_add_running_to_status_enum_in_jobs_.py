"""add running to status enum in jobs_result

Revision ID: 39405902fa31
Revises: 827f22860c04
Create Date: 2023-04-01 11:10:12.975445

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "39405902fa31"
down_revision = "827f22860c04"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""ALTER TYPE "JobStatus" ADD VALUE 'running'""")


def downgrade():
    # update all 'running' statuses back to 'pending'
    op.execute("UPDATE jobs_result UPDATE status='pending' WHERE status='running")
    # rename type name to random name so existing name can be used again
    op.execute("""ALTER TYPE "JobStatus" RENAME TO oldJobStatus""")
    # create type with original enum values
    op.execute("""CREATE TYPE "JobStatus" AS ENUM('pending', 'error', 'finished', 'deleted')""")
    # set enums to column
    op.execute(
        """ALTER TABLE jobs_result ALTER COLUMN status TYPE "JobStatus" USING status::text::"JobStatus" """
    )
    # drop the old type, cleanup
    op.execute("""DROP TYPE oldJobStatus""")
