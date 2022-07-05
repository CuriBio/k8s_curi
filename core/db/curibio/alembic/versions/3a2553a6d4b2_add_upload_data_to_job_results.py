"""add upload data to job results

Revision ID: 3a2553a6d4b2
Revises: 6dbe71e474d2
Create Date: 2022-07-01 10:47:47.761528

"""
from distutils.command.upload import upload
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "3a2553a6d4b2"
down_revision = "6dbe71e474d2"
branch_labels = None
depends_on = None


def upgrade():

    upload_type = postgresql.ENUM("mantarray", "nautilus", "pulse2d", name="UploadType")
    upload_type.create(op.get_bind())

    with op.batch_alter_table("uploads") as batch_op:
        batch_op.drop_column("object_key")
        batch_op.add_column(sa.Column("prefix", sa.VARCHAR(255), nullable=True))
        batch_op.add_column(sa.Column("filename", sa.VARCHAR(255), nullable=True))
        batch_op.add_column(
            sa.Column(
                "type",
                sa.Enum("mantarray", "nautilus", "pulse2d", name="UploadType", create_type=True),
                nullable=True,
                server_default="mantarray",
            ),
        )
        batch_op.alter_column("type", server_default=None)

    with op.batch_alter_table("jobs_result") as batch_op:
        batch_op.add_column(sa.Column("object_key", sa.VARCHAR(255), nullable=True))


def downgrade():
    upload_type = postgresql.ENUM("mantarray", "nautilus", "pulse2d", name="UploadType")
    upload_type.create(op.get_bind())

    with op.batch_alter_table("uploads") as batch_op:
        batch_op.add_column(sa.Column("object_key", sa.VARCHAR(255), nullable=True))
        batch_op.drop_column("prefix")
        batch_op.drop_column("filename")
        batch_op.drop_column("type")

    with op.batch_alter_table("jobs_result") as batch_op:
        batch_op.drop_column("object_key")
