"""Widget business rules: tenant ownership lives here, not in the routes."""
from sqlalchemy.orm import Session

from .. import models, schemas
from ..errors import NotFoundError
from ..repositories import widget_repo


def create_widget(db: Session, tenant_id: str, payload: schemas.WidgetCreate) -> models.Widget:
    widget = models.Widget(**payload.model_dump(mode="json"), tenant_id=tenant_id)
    return widget_repo.add(db, widget)


def list_widgets(db: Session, tenant_id: str) -> list[models.Widget]:
    return widget_repo.list_for_tenant(db, tenant_id)


def get_owned_widget(db: Session, widget_id: str, tenant_id: str) -> models.Widget:
    """Another tenant's widget is indistinguishable from a missing one (404)."""
    widget = widget_repo.get_for_tenant(db, widget_id, tenant_id)
    if widget is None:
        raise NotFoundError("Widget not found")
    return widget


def update_widget(
    db: Session, widget_id: str, tenant_id: str, payload: schemas.WidgetUpdate
) -> models.Widget:
    widget = get_owned_widget(db, widget_id, tenant_id)
    changes = payload.model_dump(mode="json", exclude_unset=True)
    # Required columns cannot be nulled out through PATCH.
    changes = {k: v for k, v in changes.items() if v is not None or k == "description"}
    return widget_repo.update(db, widget, changes)


def delete_widget(db: Session, widget_id: str, tenant_id: str) -> None:
    widget_repo.delete(db, get_owned_widget(db, widget_id, tenant_id))


def get_public_config(db: Session, widget_id: str) -> models.Widget:
    widget = widget_repo.get_public(db, widget_id)
    if widget is None:
        raise NotFoundError("Widget not found")
    return widget


def embed_snippet(widget: models.Widget, base_url: str) -> str:
    return f'<script src="{base_url.rstrip("/")}/widget.v2.js?id={widget.id}"></script>'
