import uuid
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from .database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Widget(Base):
    __tablename__ = "widgets"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)  # "signup_form" | "cta_popover"
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    fields = Column(JSON, nullable=False, default=list)
    button_text = Column(String, default="Submit")
    display_options = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String, primary_key=True, default=gen_uuid)
    widget_id = Column(String, ForeignKey("widgets.id"), nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    data = Column(JSON, nullable=False)
    ip_address = Column(String, nullable=True)
    country = Column(String, nullable=True)
    city = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())