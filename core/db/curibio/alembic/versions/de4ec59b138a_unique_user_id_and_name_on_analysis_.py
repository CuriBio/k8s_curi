"""unique user_id and name on analysis_presets

Revision ID: de4ec59b138a
Revises: 848fb69a8766
Create Date: 2024-05-02 16:22:08.798063

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "de4ec59b138a"
down_revision = "848fb69a8766"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE analysis_presets ADD CONSTRAINT unique_name_per_user UNIQUE (user_id, name)")


def downgrade():
    op.execute("ALTER TABLE analysis_presets DROP CONSTRAINT unique_name_per_user")
