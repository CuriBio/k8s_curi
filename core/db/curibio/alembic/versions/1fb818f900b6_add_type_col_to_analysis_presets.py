"""add type col to analysis presets

Revision ID: 1fb818f900b6
Revises: 86bd61c49403
Create Date: 2024-06-06 12:52:36.429879

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "1fb818f900b6"
down_revision = "86bd61c49403"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE analysis_presets ADD COLUMN type UploadType")
    op.execute("UPDATE analysis_presets SET type='mantarray'")
    op.execute("ALTER TABLE analysis_presets ALTER COLUMN type SET NOT NULL")


def downgrade():
    # this downgrade assumes that no changes have been made to this table since the upgrade has run
    # op.execute("DELETE FROM analysis_presets WHERE type='mantarray'")
    pass
