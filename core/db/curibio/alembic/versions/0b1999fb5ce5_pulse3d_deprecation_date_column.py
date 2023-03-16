"""pulse3d deprecation date column

Revision ID: 0b1999fb5ce5
Revises: 4ee06d203fad
Create Date: 2023-03-10 12:11:27.147725

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "0b1999fb5ce5"
down_revision = "4ee06d203fad"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE pulse3d_versions ADD CONSTRAINT deprecated_version_must_have_end_of_life_date CHECK(status <> 'deprecated' OR end_of_life_date IS NOT NULL)"
    )
    op.execute("ALTER TABLE pulse3d_versions ADD COLUMN end_of_life_date DATE DEFAULT null")


def downgrade():
    op.execute("ALTER TABLE pulse3d_versions DROP COLUMN end_of_life_date")
