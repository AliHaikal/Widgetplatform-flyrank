from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/widgets", tags=["widgets"])


def get_current_tenant():
    # placeholder — replaced with real Supabase JWT auth in the next step
    return "dev-tenant"


@router.post("", response_model=schemas.WidgetOut, status_code=201)
def create_widget(
    widget: schemas.WidgetCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    db_widget = models.Widget(**widget.model_dump(), tenant_id=tenant_id)
    db.add(db_widget)
    db.commit()
    db.refresh(db_widget)
    return db_widget


@router.get("", response_model=list[schemas.WidgetOut])
def list_widgets(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    return db.query(models.Widget).filter(models.Widget.tenant_id == tenant_id).all()


@router.get("/{widget_id}", response_model=schemas.WidgetOut)
def get_widget(
    widget_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    widget = db.query(models.Widget).filter(
        models.Widget.id == widget_id, models.Widget.tenant_id == tenant_id
    ).first()
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
    return widget


@router.patch("/{widget_id}", response_model=schemas.WidgetOut)
def update_widget(
    widget_id: str,
    updates: schemas.WidgetUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    widget = db.query(models.Widget).filter(
        models.Widget.id == widget_id, models.Widget.tenant_id == tenant_id
    ).first()
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(widget, field, value)
    db.commit()
    db.refresh(widget)
    return widget


@router.delete("/{widget_id}", status_code=204)
def delete_widget(
    widget_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    widget = db.query(models.Widget).filter(
        models.Widget.id == widget_id, models.Widget.tenant_id == tenant_id
    ).first()
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
    db.delete(widget)
    db.commit()