"""pulse3d deprecation date column

Revision ID: 0b1999fb5ce5
Revises: ac1e440896f9
Create Date: 2023-03-10 12:11:27.147725

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "0b1999fb5ce5"
down_revision = "ac1e440896f9"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE pulse3d_versions ADD COLUMN end_of_life_date DATE DEFAULT null")
    op.execute("UPDATE pulse3d_versions SET end_of_life_date='2024-01-01' WHERE state='deprecated'")
    op.execute(
        "ALTER TABLE pulse3d_versions ADD CONSTRAINT deprecated_version_must_have_end_of_life_date CHECK(state != 'deprecated' OR end_of_life_date IS NOT NULL)"
    )


def downgrade():
    op.execute("ALTER TABLE pulse3d_versions DROP COLUMN end_of_life_date")
