from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.post("", response_model=schemas.SubmissionOut, status_code=201)
def create_submission(
    widget_id: str,
    submission: schemas.SubmissionCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    widget = db.query(models.Widget).filter(models.Widget.id == widget_id).first()
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")

    db_submission = models.Submission(
        widget_id=widget_id,
        tenant_id=widget.tenant_id,
        data=submission.data,
        ip_address=request.client.host,
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    return db_submission