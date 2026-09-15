from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class WidgetBase(BaseModel):
    type: str  # "signup_form" | "cta_popover"
    title: str
    description: Optional[str] = None
    fields: list[dict] = Field(default_factory=list)
    button_text: str = "Submit"
    display_options: Optional[dict] = Field(default_factory=dict)


class WidgetCreate(WidgetBase):
    pass


class WidgetUpdate(BaseModel):
    type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    fields: Optional[list[dict]] = None
    button_text: Optional[str] = None
    display_options: Optional[dict] = None


class WidgetOut(WidgetBase):
    id: str
    tenant_id: str
    created_at: datetime

    class Config:
        from_attributes = True
        
class SubmissionCreate(BaseModel):
    data: dict


class SubmissionOut(BaseModel):
    id: str
    widget_id: str
    data: dict
    country: Optional[str] = None
    city: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
        
