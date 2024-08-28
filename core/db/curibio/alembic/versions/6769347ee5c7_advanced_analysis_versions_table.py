"""advanced_analysis_versions table

Revision ID: 6769347ee5c7
Revises: 6610b7f75d43
Create Date: 2024-08-27 17:21:26.580582

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "6769347ee5c7"
down_revision = "6610b7f75d43"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
CREATE TABLE advanced_analysis_versions (
    version          varchar(15) PRIMARY KEY,
    created_at       TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    state            "WorkerState" NOT NULL DEFAULT 'testing'::"WorkerState",
    end_of_life_date DATE DEFAULT null,
    CONSTRAINT deprecated_version_must_have_end_of_life_date CHECK(state != 'deprecated' OR end_of_life_date IS NOT NULL)
)
        """
    )
    op.execute(
        """
        CREATE TRIGGER set_timestamp
        BEFORE UPDATE ON advanced_analysis_versions
        FOR EACH ROW
        EXECUTE PROCEDURE trigger_set_timestamp();
        """
    )
    op.execute("GRANT SELECT ON TABLE advanced_analysis_versions TO curibio_advanced_analysis")


def downgrade():
    op.execute("REVOKE ALL PRIVILEGES ON TABLE advanced_analysis_versions FROM curibio_advanced_analysis")
    op.drop_table("advanced_analysis_versions")
