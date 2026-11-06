"""Owner dashboard: listings and aggregation, always scoped to the tenant."""
from sqlalchemy.orm import Session

from .. import models, schemas
from ..repositories import submission_repo
from . import widget_service


def list_submissions(
    db: Session, widget_id: str, tenant_id: str, limit: int, offset: int
) -> tuple[list[models.Submission], int]:
    widget_service.get_owned_widget(db, widget_id, tenant_id)
    rows = submission_repo.list_for_widget(db, widget_id, tenant_id, limit, offset)
    total = submission_repo.count_for_widget(db, widget_id, tenant_id)
    return rows, total


def widget_stats(db: Session, widget_id: str, tenant_id: str) -> schemas.WidgetStats:
    widget_service.get_owned_widget(db, widget_id, tenant_id)
    return schemas.WidgetStats(
        widget_id=widget_id,
        total=submission_repo.count_for_widget(db, widget_id, tenant_id),
        per_day=[
            schemas.DayCount(date=d, count=n)
            for d, n in submission_repo.per_day(db, widget_id, tenant_id)
        ],
        by_country=[
            schemas.CountryCount(country=c or "unknown", count=n)
            for c, n in submission_repo.by_country(db, widget_id, tenant_id)
        ],
    )


def overview(db: Session, tenant_id: str) -> list[schemas.WidgetOverview]:
    return [
        schemas.WidgetOverview(
            widget_id=wid, title=title, type=kind, total=total, last_submission_at=last
        )
        for wid, title, kind, total, last in submission_repo.overview_for_tenant(db, tenant_id)
    ]
