"""create object prediction runs table

Revision ID: 0003_prediction_runs
Revises: 0002_object_count_obs
Create Date: 2026-09-25

"""
from alembic import op
import sqlalchemy as sa

revision = "0003_prediction_runs"
down_revision = "0002_object_count_obs"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "object_prediction_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("annotated_image", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("predictions", sa.JSON(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_object_prediction_runs_model_name", "object_prediction_runs", ["model_name"])


def downgrade():
    op.drop_index("ix_object_prediction_runs_model_name", table_name="object_prediction_runs")
    op.drop_table("object_prediction_runs")
