"""add idempotency key to submissions

A retried POST carrying the same Idempotency-Key must store exactly one row.
The unique constraint is what makes that true even when two retries race.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-06
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("submissions") as batch:
        batch.add_column(sa.Column("idempotency_key", sa.String(128), nullable=True))
        batch.create_unique_constraint(
            "uq_submissions_widget_idempotency", ["widget_id", "idempotency_key"]
        )


def downgrade() -> None:
    with op.batch_alter_table("submissions") as batch:
        batch.drop_constraint("uq_submissions_widget_idempotency", type_="unique")
        batch.drop_column("idempotency_key")
