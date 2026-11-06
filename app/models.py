import uuid

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from .database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Widget(Base):
    __tablename__ = "widgets"
    __table_args__ = (Index("ix_widgets_tenant_created", "tenant_id", "created_at"),)

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(64), nullable=False)
    type = Column(String(32), nullable=False)  # "signup_form" | "cta_popover"
    title = Column(String(120), nullable=False)
    description = Column(String(500), nullable=True)
    fields = Column(JSON, nullable=False, default=list)
    button_text = Column(String(40), nullable=False, default="Submit")
    display_options = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        # A retried request with the same key can never create a second row.
        UniqueConstraint(
            "widget_id", "idempotency_key", name="uq_submissions_widget_idempotency"
        ),
        # Dashboard queries: per widget, newest first; and per tenant.
        Index("ix_submissions_widget_created", "widget_id", "created_at"),
        Index(
            "ix_submissions_tenant_widget_created",
            "tenant_id",
            "widget_id",
            "created_at",
        ),
    )

    id = Column(String(36), primary_key=True, default=gen_uuid)
    widget_id = Column(
        String(36), ForeignKey("widgets.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id = Column(String(64), nullable=False)
    data = Column(JSON, nullable=False)
    ip_address = Column(String(64), nullable=True)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    idempotency_key = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
