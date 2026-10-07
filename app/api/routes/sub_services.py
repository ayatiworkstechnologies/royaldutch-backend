from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession, get_current_user
from app.core.permissions import require_permission
from app.models.enums import RecordStatus
from app.models.service import Service
from app.models.sub_service import SubService
from app.models.user import User
from app.schemas.sub_service import SubServiceCreate, SubServiceRead, SubServiceUpdate
from app.services.audit_service import model_snapshot, write_audit_log
from app.services.catalog_validation import commit_catalog

router = APIRouter(prefix="/services/{service_id}/sub-services", tags=["sub-services"])
admin_router = APIRouter(prefix="/sub-services", tags=["sub-services"])
manage = [Depends(require_permission("services.manage"))]


@admin_router.get("", response_model=list[SubServiceRead], dependencies=manage)
def list_all_sub_services(db: DbSession, include_inactive: bool = Query(default=True)):
    query = select(SubService).options(joinedload(SubService.service)).order_by(SubService.service_id, SubService.id)
    if not include_inactive:
        query = query.where(SubService.status == RecordStatus.active)
    return list(db.scalars(query).all())


def get_parent(db, service_id, include_inactive=True):
    parent = db.get(Service, service_id)
    if parent is None or (not include_inactive and (
        parent.status != RecordStatus.active or parent.category.status != RecordStatus.active
    )):
        raise HTTPException(status_code=404, detail="Service not found")
    return parent


def get_child(db, service_id, sub_service_id):
    get_parent(db, service_id)
    child = db.get(SubService, sub_service_id)
    if child is None or child.service_id != service_id:
        raise HTTPException(status_code=404, detail="Sub-service not found")
    return child


@router.get("", response_model=list[SubServiceRead])
def list_sub_services(service_id: int, db: DbSession, include_inactive: bool = Query(default=False)):
    get_parent(db, service_id, include_inactive)
    query = select(SubService).where(SubService.service_id == service_id).order_by(SubService.id)
    if not include_inactive:
        query = query.where(SubService.status == RecordStatus.active)
    return list(db.scalars(query).all())


@router.post("", response_model=SubServiceRead, dependencies=manage)
def create_sub_service(service_id: int, data: SubServiceCreate, db: DbSession, request: Request, user: User = Depends(get_current_user)):
    get_parent(db, service_id, include_inactive=False)
    existing = db.scalar(
        select(SubService).where(
            SubService.service_id == service_id,
            SubService.slug == data.slug,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Sub-service slug '{data.slug}' already exists for this service; edit sub-service {existing.id} instead",
        )
    child = SubService(service_id=service_id, **data.model_dump())
    db.add(child)
    # Flush through the shared conflict handler before recording the generated ID.
    commit_catalog(db)
    db.refresh(child)
    write_audit_log(db, action="sub_service.create", entity_type="SubService", entity_id=child.id, user=user, request=request, new_value=model_snapshot(child))
    db.commit()
    return child


@router.patch("/{sub_service_id}", response_model=SubServiceRead, dependencies=manage)
def update_sub_service(service_id: int, sub_service_id: int, data: SubServiceUpdate, db: DbSession, request: Request, user: User = Depends(get_current_user)):
    child = get_child(db, service_id, sub_service_id)
    old = model_snapshot(child)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(child, field, value)
    write_audit_log(db, action="sub_service.update", entity_type="SubService", entity_id=child.id, user=user, request=request, old_value=old, new_value=model_snapshot(child))
    commit_catalog(db)
    db.refresh(child)
    return child


@router.delete("/{sub_service_id}", dependencies=manage)
def delete_sub_service(service_id: int, sub_service_id: int, db: DbSession, request: Request, user: User = Depends(get_current_user)):
    child = get_child(db, service_id, sub_service_id)
    write_audit_log(db, action="sub_service.delete", entity_type="SubService", entity_id=child.id, user=user, request=request, old_value=model_snapshot(child))
    db.delete(child)
    commit_catalog(db)
    return {"message": "Sub-service deleted"}
