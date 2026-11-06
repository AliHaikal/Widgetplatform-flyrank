"""Widget routes. HTTP only: parse, call the service, shape the response."""
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_tenant
from ..database import get_db
from ..services import widget_service

router = APIRouter(prefix="/widgets", tags=["widgets"])


# --- owner API (authenticated, tenant-isolated) -------------------------------

@router.post("", response_model=schemas.WidgetOut, status_code=201)
def create_widget(
    payload: schemas.WidgetCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    return widget_service.create_widget(db, tenant_id, payload)


@router.get("", response_model=list[schemas.WidgetOut])
def list_widgets(
    db: Session = Depends(get_db), tenant_id: str = Depends(get_current_tenant)
):
    return widget_service.list_widgets(db, tenant_id)


# --- public delivery (declared before "/{widget_id}" so paths stay unambiguous)

@router.get("/{widget_id}/config", response_model=schemas.WidgetConfigOut)
def get_widget_config(widget_id: str, response: Response, db: Session = Depends(get_db)):
    """Public, CORS-open, short-lived cache: owner edits show up within a minute."""
    widget = widget_service.get_public_config(db, widget_id)
    response.headers["Cache-Control"] = "public, max-age=60"
    return widget


@router.get("/{widget_id}/embed", response_model=schemas.EmbedOut)
def get_embed_snippet(
    widget_id: str,
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    widget = widget_service.get_owned_widget(db, widget_id, tenant_id)
    return {"snippet": widget_service.embed_snippet(widget, str(request.base_url))}


@router.get("/{widget_id}", response_model=schemas.WidgetOut)
def get_widget(
    widget_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    return widget_service.get_owned_widget(db, widget_id, tenant_id)


@router.patch("/{widget_id}", response_model=schemas.WidgetOut)
def update_widget(
    widget_id: str,
    payload: schemas.WidgetUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    return widget_service.update_widget(db, widget_id, tenant_id, payload)


@router.delete("/{widget_id}", status_code=204)
def delete_widget(
    widget_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    widget_service.delete_widget(db, widget_id, tenant_id)
    return Response(status_code=204)
