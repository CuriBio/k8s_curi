"""add type col to analysis presets

Revision ID: 1fb818f900b6
Revises: 34ba5254bfe1
Create Date: 2024-06-06 12:52:36.429879

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "1fb818f900b6"
down_revision = "34ba5254bfe1"
branch_labels = None
depends_on = None


def upgrade():
    op.execute('ALTER TABLE analysis_presets ADD COLUMN "type" "UploadType"')
    op.execute("UPDATE analysis_presets SET type='mantarray'")
    op.execute('ALTER TABLE analysis_presets ALTER COLUMN "type" SET NOT NULL')
    op.execute("ALTER TABLE analysis_presets DROP CONSTRAINT unique_name_per_user")
    op.execute(
        'ALTER TABLE analysis_presets ADD CONSTRAINT unique_name_type_per_user UNIQUE (user_id, name, "type")'
    )
    op.execute(
        """INSERT INTO analysis_presets (user_id, name, parameters, "type") SELECT user_id, name, parameters, 'nautilai' FROM analysis_presets"""
    )


def downgrade():
    # this downgrade assumes that no changes have been made to this table since the upgrade has run
    op.execute("DELETE FROM analysis_presets WHERE type='nautilai'")
    op.execute("ALTER TABLE analysis_presets DROP CONSTRAINT unique_name_type_per_user")
    op.execute("ALTER TABLE analysis_presets ADD CONSTRAINT unique_name_per_user UNIQUE (user_id, name)")
    op.execute('ALTER TABLE analysis_presets DROP COLUMN "type"')
