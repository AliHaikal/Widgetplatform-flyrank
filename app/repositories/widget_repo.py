"""Data access for widgets. No business rules, no HTTP."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models


def add(db: Session, widget: models.Widget) -> models.Widget:
    db.add(widget)
    db.commit()
    db.refresh(widget)
    return widget


def list_for_tenant(db: Session, tenant_id: str) -> list[models.Widget]:
    stmt = (
        select(models.Widget)
        .where(models.Widget.tenant_id == tenant_id)
        .order_by(models.Widget.created_at.desc(), models.Widget.id)
    )
    return list(db.scalars(stmt))


def get_for_tenant(db: Session, widget_id: str, tenant_id: str) -> models.Widget | None:
    stmt = select(models.Widget).where(
        models.Widget.id == widget_id, models.Widget.tenant_id == tenant_id
    )
    return db.scalars(stmt).first()


def get_public(db: Session, widget_id: str) -> models.Widget | None:
    return db.get(models.Widget, widget_id)


def update(db: Session, widget: models.Widget, changes: dict) -> models.Widget:
    for key, value in changes.items():
        setattr(widget, key, value)
    db.commit()
    db.refresh(widget)
    return widget


def delete(db: Session, widget: models.Widget) -> None:
    db.delete(widget)  # submissions go with it (ON DELETE CASCADE)
    db.commit()
