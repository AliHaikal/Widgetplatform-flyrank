"""Data access for submissions, including the dashboard aggregations."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models

S = models.Submission


def add(db: Session, submission: models.Submission) -> models.Submission:
    db.add(submission)
    db.commit()  # may raise IntegrityError on a duplicate idempotency key
    db.refresh(submission)
    return submission


def get_by_idempotency_key(db: Session, widget_id: str, key: str) -> models.Submission | None:
    stmt = select(S).where(S.widget_id == widget_id, S.idempotency_key == key)
    return db.scalars(stmt).first()


def list_for_widget(
    db: Session, widget_id: str, tenant_id: str, limit: int, offset: int
) -> list[models.Submission]:
    stmt = (
        select(S)
        .where(S.widget_id == widget_id, S.tenant_id == tenant_id)
        .order_by(S.created_at.desc(), S.id)
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt))


def count_for_widget(db: Session, widget_id: str, tenant_id: str) -> int:
    stmt = select(func.count()).select_from(S).where(
        S.widget_id == widget_id, S.tenant_id == tenant_id
    )
    return db.scalar(stmt) or 0


def per_day(db: Session, widget_id: str, tenant_id: str) -> list[tuple[str, int]]:
    day = func.date(S.created_at)
    stmt = (
        select(day, func.count())
        .where(S.widget_id == widget_id, S.tenant_id == tenant_id)
        .group_by(day)
        .order_by(day)
    )
    return [(str(d), n) for d, n in db.execute(stmt)]


def by_country(db: Session, widget_id: str, tenant_id: str) -> list[tuple[str | None, int]]:
    stmt = (
        select(S.country, func.count())
        .where(S.widget_id == widget_id, S.tenant_id == tenant_id)
        .group_by(S.country)
        .order_by(func.count().desc(), S.country)
    )
    return [(c, n) for c, n in db.execute(stmt)]


def overview_for_tenant(db: Session, tenant_id: str):
    W = models.Widget
    stmt = (
        select(W.id, W.title, W.type, func.count(S.id), func.max(S.created_at))
        .outerjoin(S, S.widget_id == W.id)
        .where(W.tenant_id == tenant_id)
        .group_by(W.id, W.title, W.type, W.created_at)
        .order_by(W.created_at.desc(), W.id)
    )
    return list(db.execute(stmt))
