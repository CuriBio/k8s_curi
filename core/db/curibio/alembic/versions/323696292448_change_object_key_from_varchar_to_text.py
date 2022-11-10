"""change object_key from VARCHAR to TEXT

Revision ID: 323696292448
Revises: c22ab281fe0b
Create Date: 2022-11-10 13:12:32.738628

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "323696292448"
down_revision = "c22ab281fe0b"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE jobs_result ALTER COLUMN object_key TYPE TEXT")
    op.execute("ALTER TABLE mantarray_session_log_files ALTER COLUMN object_key TYPE TEXT")
    op.execute("ALTER TABLE uploads ALTER COLUMN prefix TYPE TEXT")
    op.execute("ALTER TABLE uploads ALTER COLUMN filename TYPE TEXT")


def downgrade():
    op.execute("ALTER TABLE jobs_result ALTER COLUMN object_key TYPE VARCHAR(255)")
    op.execute("ALTER TABLE mantarray_session_log_files ALTER COLUMN object_key TYPE VARCHAR(255)")
    op.execute("ALTER TABLE uploads ALTER COLUMN prefix TYPE VARCHAR(255)")
    op.execute("ALTER TABLE uploads ALTER COLUMN filename TYPE VARCHAR(255)")
