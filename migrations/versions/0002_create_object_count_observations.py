"""create object count observations table

Revision ID: 0002_object_count_obs
Revises: 0001_create_object_counts
Create Date: 2026-09-25

"""
from alembic import op
import sqlalchemy as sa

revision = "0002_object_count_obs"
down_revision = "0001_create_object_counts"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "object_count_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("model_display_name", sa.String(), nullable=False),
        sa.Column("serving_name", sa.String(), nullable=False),
        sa.Column("object_class", sa.String(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_object_count_observations_model_name", "object_count_observations", ["model_name"])
    op.create_index("ix_object_count_observations_serving_name", "object_count_observations", ["serving_name"])
    op.create_index("ix_object_count_observations_object_class", "object_count_observations", ["object_class"])


def downgrade():
    op.drop_index("ix_object_count_observations_object_class", table_name="object_count_observations")
    op.drop_index("ix_object_count_observations_serving_name", table_name="object_count_observations")
    op.drop_index("ix_object_count_observations_model_name", table_name="object_count_observations")
    op.drop_table("object_count_observations")
