"""Public submission endpoint (any origin, CORS-enabled, protected).

Protection order: rate limit and body size are enforced by middleware before
this function runs; Pydantic validates the shape; the service validates values
against the widget; the confirmation email is a background job.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, Header, Request, Response
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..net import client_ip
from ..notify import send_with_retry
from ..services import submission_service

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.post("", response_model=schemas.SubmissionOut, status_code=201)
def create_submission(
    widget_id: str,
    payload: schemas.SubmissionCreate,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9_.:-]+$",
    ),
    db: Session = Depends(get_db),
):
    result = submission_service.create_submission(
        db, widget_id, payload, client_ip(request.scope), idempotency_key
    )
    if not result.created:
        # Same key seen before: return the original row, store nothing, send nothing.
        response.status_code = 200
        response.headers["Idempotent-Replay"] = "true"
        return result.submission

    background_tasks.add_task(send_with_retry, result.widget_title, result.submission.data)
    return result.submission
