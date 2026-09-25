"""create object counts table

Revision ID: 0001_create_object_counts
Revises:
Create Date: 2026-09-25

"""
from alembic import op
import sqlalchemy as sa

revision = "0001_create_object_counts"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "object_counts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("object_class", sa.String(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_object_counts_object_class", "object_counts", ["object_class"])
    op.create_index("ix_object_counts_object_class", "object_counts", ["object_class"])


def downgrade():
    op.drop_index("ix_object_counts_object_class", table_name="object_counts")
    op.drop_constraint("uq_object_counts_object_class", "object_counts", type_="unique")
    op.drop_table("object_counts")
