"""pulse3d deprecation date column

Revision ID: 0b1999fb5ce5
Revises: b1c798d03073
Create Date: 2023-03-10 12:11:27.147725

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "0b1999fb5ce5"
down_revision = "b1c798d03073"
branch_labels = None
depends_on = None


def upgrade():
    # can not remove this new enum value unless deleting it and remaking a new enum type
    op.execute("ALTER TYPE WorkerState ADD VALUE 'removed'")
    op.execute("ALTER TABLE pulse3d_versions ADD COLUMN end_of_life_date DATE DEFAULT null")
    # deprecate all versions of pulse3d before 0.28.2 inclusive
    op.execute("UPDATE pulse3d_versions SET state = 'deprecated' WHERE version <= '0.28.2'")


def downgrade():
    op.execute("ALTER TABLE pulse3d_versions DROP COLUMN end_of_life_date")
    op.execute("UPDATE pulse3d_versions SET state = 'external' WHERE version <= '0.28.2'")
