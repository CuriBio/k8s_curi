"""update jobs_queue for advanced analysis

Revision ID: 4d9f2cabaced
Revises: 73f5610ab1fa
Create Date: 2024-08-15 10:06:13.552256

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "4d9f2cabaced"
down_revision = "73f5610ab1fa"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE jobs_queue ALTER COLUMN upload_id DROP NOT NULL")
    op.execute("ALTER TABLE jobs_queue ADD COLUMN sources uuid[]")
    op.execute(
        "ALTER TABLE jobs_queue ADD CONSTRAINT exactly_one_source_col_set CHECK((upload_id IS NULL) != (sources IS NULL))"
    )


def downgrade():
    op.execute("ALTER TABLE jobs_queue DROP CONSTRAINT exactly_one_source_col_set")
    op.execute("ALTER TABLE jobs_queue DROP COLUMN sources")
    op.execute("ALTER TABLE jobs_queue ALTER COLUMN upload_id SET NOT NULL")
