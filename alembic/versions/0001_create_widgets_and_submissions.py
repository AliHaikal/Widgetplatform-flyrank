"""create widgets and submissions

Revision ID: 0001
Revises:
Create Date: 2026-11-06
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "widgets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("fields", sa.JSON(), nullable=False),
        sa.Column("button_text", sa.String(40), nullable=False),
        sa.Column("display_options", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_widgets_tenant_created", "widgets", ["tenant_id", "created_at"])

    op.create_table(
        "submissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "widget_id",
            sa.String(36),
            sa.ForeignKey("widgets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_submissions_widget_created", "submissions", ["widget_id", "created_at"]
    )
    op.create_index(
        "ix_submissions_tenant_widget_created",
        "submissions",
        ["tenant_id", "widget_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_submissions_tenant_widget_created", table_name="submissions")
    op.drop_index("ix_submissions_widget_created", table_name="submissions")
    op.drop_table("submissions")
    op.drop_index("ix_widgets_tenant_created", table_name="widgets")
    op.drop_table("widgets")
