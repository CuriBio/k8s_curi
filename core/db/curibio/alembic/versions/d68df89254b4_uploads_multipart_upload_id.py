"""uploads.multipart_upload_id

Revision ID: d68df89254b4
Revises: 72b7aa851310
Create Date: 2025-09-26 15:01:23.480737

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "d68df89254b4"
down_revision = "72b7aa851310"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE uploads ADD COLUMN multipart_upload_id VARCHAR(256)")


def downgrade():
    op.execute("ALTER TABLE uploads DROP COLUMN multipart_upload_id")
