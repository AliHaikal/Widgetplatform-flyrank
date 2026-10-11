from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from .widgets import get_current_tenant

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _owned_widget(db: Session, widget_id: str, tenant_id: str):
    widget = db.query(models.Widget).filter(
        models.Widget.id == widget_id, models.Widget.tenant_id == tenant_id
    ).first()
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
    return widget


@router.get("/widgets/{widget_id}/submissions", response_model=list[schemas.SubmissionOut])
def list_submissions(
    widget_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    _owned_widget(db, widget_id, tenant_id)
    return (
        db.query(models.Submission)
        .filter(
            models.Submission.widget_id == widget_id,
            models.Submission.tenant_id == tenant_id,
        )
        .order_by(models.Submission.created_at.desc())
        .all()
    )


@router.get("/widgets/{widget_id}/stats")
def widget_stats(
    widget_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    _owned_widget(db, widget_id, tenant_id)
    base = db.query(models.Submission).filter(
        models.Submission.widget_id == widget_id,
        models.Submission.tenant_id == tenant_id,
    )

    total = base.count()

    per_day = (
        base.with_entities(
            func.date(models.Submission.created_at), func.count()
        )
        .group_by(func.date(models.Submission.created_at))
        .order_by(func.date(models.Submission.created_at))
        .all()
    )

    by_country = (
        base.with_entities(models.Submission.country, func.count())
        .group_by(models.Submission.country)
        .all()
    )

    return {
        "widget_id": widget_id,
        "total": total,
        "per_day": [{"date": str(d), "count": c} for d, c in per_day],
        "by_country": [
            {"country": c or "unknown", "count": n} for c, n in by_country
        ],
    }
    