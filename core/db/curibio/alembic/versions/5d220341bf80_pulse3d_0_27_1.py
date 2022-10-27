"""pulse3D 0.27.1

Revision ID: 5d220341bf80
Revises: 705b8a7903c8
Create Date: 2022-10-20 13:51:12.789508

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "5d220341bf80"
down_revision = "705b8a7903c8"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO pulse3d_versions (version, state) VALUES ('0.27.1', 'external')")
    op.execute("UPDATE pulse3d_versions SET state='deprecated' WHERE version='0.27.0'")


def downgrade():
    op.execute("DELETE FROM pulse3d_versions WHERE version='0.27.1'")
    op.execute("UPDATE pulse3d_versions SET state='external' WHERE version='0.27.0'")
