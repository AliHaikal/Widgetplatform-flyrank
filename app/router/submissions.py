from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..limiter import limiter
from ..geo import lookup_geo
from ..notify import send_with_retry

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.post("", response_model=schemas.SubmissionOut, status_code=201)
@limiter.limit("5/minute")
def create_submission(
    widget_id: str,
    submission: schemas.SubmissionCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    widget = db.query(models.Widget).filter(models.Widget.id == widget_id).first()
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")

    ip = request.client.host
    geo = lookup_geo(ip) or {}

    db_submission = models.Submission(
        widget_id=widget_id,
        tenant_id=widget.tenant_id,
        data=submission.data,
        ip_address=ip,
        country=geo.get("country"),
        city=geo.get("city"),
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)

    background_tasks.add_task(send_with_retry, widget.title, submission.data)

    return db_submission