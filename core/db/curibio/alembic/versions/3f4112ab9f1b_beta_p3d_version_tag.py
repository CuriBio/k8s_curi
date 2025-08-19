"""beta p3d version tag

Revision ID: 3f4112ab9f1b
Revises: c2f9e584aae2
Create Date: 2025-08-19 13:27:39.270082

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "3f4112ab9f1b"
down_revision = "c2f9e584aae2"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""ALTER TYPE "WorkerState" ADD VALUE 'beta'""")
    op.execute("""ALTER TYPE "WorkerState" RENAME TO "VersionState" """)


TABLES = ("pulse3d_versions", "advanced_analysis_versions")


def downgrade():
    # change all 'beta' versions to 'testing'
    for t in TABLES:
        op.execute(f"UPDATE {t} SET state='testing' WHERE state='beta'")
    # create type with original enum values
    op.execute("""CREATE TYPE "WorkerState" AS ENUM('testing', 'internal', 'external', 'deprecated')""")
    for t in TABLES:
        # drop default so that changing the type of the column doesn't fail
        op.execute(f"ALTER TABLE {t} ALTER COLUMN state DROP DEFAULT")
        # drop constraint as well
        op.execute(f"ALTER TABLE {t} DROP CONSTRAINT deprecated_version_must_have_end_of_life_date")
        op.execute(
            f"""ALTER TABLE {t} ALTER COLUMN state TYPE "WorkerState" USING state::text::"WorkerState" """
        )
        op.execute(f"""ALTER TABLE {t} ALTER COLUMN state SET DEFAULT 'testing'::"WorkerState" """)
        op.execute(
            f"ALTER TABLE {t} ADD CONSTRAINT deprecated_version_must_have_end_of_life_date CHECK(state != 'deprecated' OR end_of_life_date IS NOT NULL)"
        )
        # add default back
    # drop the old type, cleanup
    op.execute("""DROP TYPE "VersionState" """)
