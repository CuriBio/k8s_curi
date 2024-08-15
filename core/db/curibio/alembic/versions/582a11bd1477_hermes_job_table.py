"""advanced analysis table

Revision ID: 582a11bd1477
Revises: 4d9f2cabaced
Create Date: 2024-08-15 10:52:28.989039

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "582a11bd1477"
down_revision = "4d9f2cabaced"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TYPE "AdvancedAnalysisType" AS ENUM ('longitudinal', 'overlay')""")
    op.execute(
        """
        CREATE TABLE advanced_analysis_result (
            id          uuid PRIMARY KEY,
            user_id     uuid NOT NULL,
            customer_id uuid NOT NULL,
            type        "AdvancedAnalysisType" NOT NULL,
            status      "JobStatus" NOT NULL,
            sources     uuid[] NOT NULL,
            meta        jsonb DEFAULT '{}'::jsonb,
            created_at  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            finished_at TIMESTAMP WITHOUT TIME ZONE,
            runtime     double precision,
            s3_prefix   text,
            name        text,
            CONSTRAINT fk_advanced_analysis_result_customers FOREIGN KEY (customer_id) REFERENCES customers(id),
            CONSTRAINT fk_advanced_analysis_result_users FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )


def downgrade():
    op.execute("DROP TABLE advanced_analysis_result")
    op.execute('DROP TYPE "AdvancedAnalysisType"')
