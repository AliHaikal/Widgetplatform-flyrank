"""The visitor submission pipeline.

    widget exists? -> replay of an Idempotency-Key? -> validate against the
    widget's fields -> geo enrichment (degrades) -> store

The confirmation email is NOT here: the router schedules it as a background
job only for a newly stored submission, never for a replay.
"""
import re
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..errors import FieldValidationError, NotFoundError
from ..geo import lookup_geo
from ..repositories import submission_repo, widget_repo

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE = re.compile(r"^[0-9+()\-\s]{5,20}$")
_MAX_LEN = {"text": 255, "email": 254, "tel": 20, "textarea": 2000}


@dataclass
class SubmissionResult:
    submission: models.Submission
    widget_title: str
    created: bool  # False => replay of an earlier request with the same key


def validate_against_widget(widget: models.Widget, data: dict) -> dict:
    """Check submitted values against the widget's field definitions."""
    definitions = {f["name"]: f for f in widget.fields}
    errors: list[dict] = []
    cleaned: dict = {}

    for name in data:
        if name not in definitions:
            errors.append({"field": name, "msg": "Unknown field"})

    for name, definition in definitions.items():
        value = data.get(name)
        if isinstance(value, str):
            value = value.strip()
        if value is None or value == "":
            if definition.get("required"):
                errors.append({"field": name, "msg": "This field is required"})
            continue

        kind = definition.get("type", "text")
        if kind == "number":
            if isinstance(value, bool) or not _is_number(value):
                errors.append({"field": name, "msg": "Must be a number"})
                continue
        else:
            if not isinstance(value, str):
                errors.append({"field": name, "msg": "Must be text"})
                continue
            if len(value) > _MAX_LEN.get(kind, 255):
                errors.append({"field": name, "msg": "Value is too long"})
                continue
            if kind == "email" and not _EMAIL.match(value):
                errors.append({"field": name, "msg": "Must be a valid email address"})
                continue
            if kind == "tel" and not _PHONE.match(value):
                errors.append({"field": name, "msg": "Must be a valid phone number"})
                continue
        cleaned[name] = value

    if errors:
        raise FieldValidationError(errors)
    return cleaned


def _is_number(value) -> bool:
    if isinstance(value, (int, float)):
        return True
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def create_submission(
    db: Session,
    widget_id: str,
    payload: schemas.SubmissionCreate,
    ip: str,
    idempotency_key: str | None,
) -> SubmissionResult:
    widget = widget_repo.get_public(db, widget_id)
    if widget is None:
        raise NotFoundError("Widget not found")

    if idempotency_key:
        earlier = submission_repo.get_by_idempotency_key(db, widget_id, idempotency_key)
        if earlier is not None:
            return SubmissionResult(earlier, widget.title, created=False)

    cleaned = validate_against_widget(widget, payload.data)
    geo = lookup_geo(ip) or {}

    submission = models.Submission(
        widget_id=widget.id,
        tenant_id=widget.tenant_id,
        data=cleaned,
        ip_address=ip,
        country=geo.get("country"),
        city=geo.get("city"),
        idempotency_key=idempotency_key,
    )
    try:
        submission_repo.add(db, submission)
    except IntegrityError:
        # Two identical retries raced: the unique constraint let exactly one in.
        db.rollback()
        if idempotency_key:
            earlier = submission_repo.get_by_idempotency_key(db, widget_id, idempotency_key)
            if earlier is not None:
                return SubmissionResult(earlier, widget.title, created=False)
        raise
    return SubmissionResult(submission, widget.title, created=True)
