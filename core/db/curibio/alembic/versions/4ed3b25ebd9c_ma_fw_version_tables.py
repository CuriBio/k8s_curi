"""MA FW version tables

Revision ID: 4ed3b25ebd9c
Revises: c8b48ddce1ec
Create Date: 2023-11-15 12:25:12.457951

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = "4ed3b25ebd9c"
down_revision = "c8b48ddce1ec"
branch_labels = None
depends_on = None


def upgrade():
    states = ("internal", "external")

    op.create_table(
        "ma_main_firmware",
        sa.Column("version", sa.VARCHAR(15), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), server_default=func.now(), nullable=False),
        sa.Column(
            "state",
            sa.Enum(*states, name="FirmwareState", create_type=True),
            server_default=states[0],
            nullable=False,
        ),
        sa.Column("min_ma_controller_version", sa.VARCHAR(15), nullable=True),
        sa.Column("min_sting_controller_version", sa.VARCHAR(15), nullable=True),
    )

    op.create_table(
        "ma_channel_firmware",
        sa.Column("version", sa.VARCHAR(15), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), server_default=func.now(), nullable=False),
        sa.Column(
            "state",
            sa.Enum(*states, name="FirmwareState", create_type=True),
            server_default=states[0],
            nullable=False,
        ),
        sa.Column("main_fw_version", sa.VARCHAR(15), nullable=False),
        sa.ForeignKeyConstraint(["main_fw_version"], ["ma_main_firmware.version"], ondelete="CASCADE"),
        sa.Column("hw_version", sa.VARCHAR(15), nullable=False),
    )

    for table in ("ma_controllers", "sting_controllers"):
        op.create_table(
            table,
            sa.Column("version", sa.VARCHAR(15), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=False), server_default=func.now(), nullable=False),
        )

    for table in ("ma_main_firmware", "ma_channel_firmware", "ma_controllers", "sting_controllers"):
        op.execute(
            f"""
            CREATE TRIGGER set_timestamp
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE PROCEDURE trigger_set_timestamp();
            """
        )

        op.execute(f"GRANT ALL PRIVILEGES ON TABLE {table} TO curibio_mantarray")
        op.execute(f"GRANT SELECT ON TABLE {table} TO curibio_mantarray_ro")


def downgrade():
    for table in ("ma_main_firmware", "ma_channel_firmware", "ma_controllers", "sting_controllers"):
        op.execute(f"REVOKE ALL PRIVILEGES ON TABLE {table} FROM curibio_mantarray")
        op.execute(f"REVOKE ALL PRIVILEGES ON TABLE {table} FROM curibio_mantarray_ro")

        op.execute(f"DROP TABLE {table} CASCADE")

    op.execute('DROP TYPE "FirmwareState" CASCADE')
