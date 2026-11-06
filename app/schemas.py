from datetime import datetime
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

FieldType = Literal["text", "email", "tel", "number", "textarea"]
WidgetType = Literal["signup_form", "cta_popover"]
Scalar = Union[str, int, float, bool, None]


class FieldDef(BaseModel):
    model_config = {"extra": "forbid"}

    name: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_]{0,63}$")
    label: str = Field(min_length=1, max_length=100)
    type: FieldType = "text"
    required: bool = False


class DisplayOptions(BaseModel):
    """Presentation settings. For cta_popover widgets the form opens from a button."""

    model_config = {"extra": "forbid"}

    trigger_label: str = Field(default="Sign up", min_length=1, max_length=40)
    position: Literal["bottom-right", "bottom-left"] = "bottom-right"
    delay_seconds: int = Field(default=0, ge=0, le=120)
    success_message: str = Field(default="Thanks, submitted!", max_length=200)


class WidgetBase(BaseModel):
    model_config = {"extra": "forbid"}

    type: WidgetType
    title: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    fields: list[FieldDef] = Field(min_length=1, max_length=20)
    button_text: str = Field(default="Submit", min_length=1, max_length=40)
    display_options: DisplayOptions = Field(default_factory=DisplayOptions)


class WidgetCreate(WidgetBase):
    pass


class WidgetUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    type: Optional[WidgetType] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    fields: Optional[list[FieldDef]] = Field(default=None, min_length=1, max_length=20)
    button_text: Optional[str] = Field(default=None, min_length=1, max_length=40)
    display_options: Optional[DisplayOptions] = None


class WidgetOut(WidgetBase):
    model_config = {"from_attributes": True}

    id: str
    tenant_id: str
    created_at: datetime


class WidgetConfigOut(BaseModel):
    """Public payload: no tenant id, nothing the owner didn't mean to publish."""

    model_config = {"from_attributes": True}

    id: str
    type: WidgetType
    title: str
    description: Optional[str]
    fields: list[FieldDef]
    button_text: str
    display_options: DisplayOptions


class EmbedOut(BaseModel):
    snippet: str


class SubmissionCreate(BaseModel):
    model_config = {"extra": "forbid"}

    data: dict[str, Scalar] = Field(max_length=20)
    # Honeypot: hidden from humans, bots fill it. Any content fails validation.
    honeypot: Optional[str] = Field(default=None, max_length=0)

    @field_validator("data")
    @classmethod
    def _bounded_values(cls, value):
        for key, item in value.items():
            if len(key) > 64:
                raise ValueError("field names must be 64 characters or fewer")
            if isinstance(item, str) and len(item) > 2000:
                raise ValueError(f"value for '{key}' is too long (max 2000 characters)")
        return value


class SubmissionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    widget_id: str
    data: dict
    country: Optional[str] = None
    city: Optional[str] = None
    created_at: datetime


class DayCount(BaseModel):
    date: str
    count: int


class CountryCount(BaseModel):
    country: str
    count: int


class WidgetStats(BaseModel):
    widget_id: str
    total: int
    per_day: list[DayCount]
    by_country: list[CountryCount]


class WidgetOverview(BaseModel):
    widget_id: str
    title: str
    type: str
    total: int
    last_submission_at: Optional[datetime] = None
