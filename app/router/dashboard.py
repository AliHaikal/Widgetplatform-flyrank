from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_tenant
from ..database import get_db
from ..services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=list[schemas.WidgetOverview])
def overview(db: Session = Depends(get_db), tenant_id: str = Depends(get_current_tenant)):
    """Per-widget totals for the signed-in owner."""
    return dashboard_service.overview(db, tenant_id)


@router.get(
    "/widgets/{widget_id}/submissions", response_model=list[schemas.SubmissionOut]
)
def list_submissions(
    widget_id: str,
    response: Response,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    rows, total = dashboard_service.list_submissions(db, widget_id, tenant_id, limit, offset)
    response.headers["X-Total-Count"] = str(total)
    return rows


@router.get("/widgets/{widget_id}/stats", response_model=schemas.WidgetStats)
def widget_stats(
    widget_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    return dashboard_service.widget_stats(db, widget_id, tenant_id)
