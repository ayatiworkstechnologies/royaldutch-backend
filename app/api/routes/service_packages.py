from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession, get_current_user
from app.core.permissions import require_permission
from app.models.enums import RecordStatus
from app.models.service_package import ServicePackage
from app.models.sub_service import SubService
from app.models.user import User
from app.schemas.service_package import ServicePackageCreate, ServicePackageRead, ServicePackageUpdate
from app.services.audit_service import model_snapshot, write_audit_log
from app.services.catalog_validation import commit_catalog

router = APIRouter(prefix="/sub-services/{sub_service_id}/packages", tags=["packages"])
admin_router = APIRouter(prefix="/packages", tags=["packages"])
manage = [Depends(require_permission("services.manage"))]


def get_parent(db, sub_service_id: int, include_inactive: bool = True):
    parent = db.get(SubService, sub_service_id)
    if parent is None or (not include_inactive and parent.status != RecordStatus.active):
        raise HTTPException(status_code=404, detail="Sub-service not found")
    return parent


def get_package(db, sub_service_id: int, package_id: int):
    get_parent(db, sub_service_id)
    package = db.get(ServicePackage, package_id)
    if package is None or package.sub_service_id != sub_service_id:
        raise HTTPException(status_code=404, detail="Package not found")
    return package


@admin_router.get("", response_model=list[ServicePackageRead], dependencies=manage)
def list_all_packages(db: DbSession, include_inactive: bool = Query(default=True)):
    query = select(ServicePackage).options(joinedload(ServicePackage.sub_service)).order_by(ServicePackage.sub_service_id, ServicePackage.id)
    if not include_inactive:
        query = query.where(ServicePackage.status == RecordStatus.active)
    return list(db.scalars(query).all())


@router.get("", response_model=list[ServicePackageRead])
def list_packages(sub_service_id: int, db: DbSession, include_inactive: bool = Query(default=False)):
    get_parent(db, sub_service_id, include_inactive)
    query = select(ServicePackage).where(ServicePackage.sub_service_id == sub_service_id).order_by(ServicePackage.id)
    if not include_inactive:
        query = query.where(ServicePackage.status == RecordStatus.active)
    return list(db.scalars(query).all())


@router.post("", response_model=ServicePackageRead, dependencies=manage)
def create_package(sub_service_id: int, data: ServicePackageCreate, db: DbSession, request: Request, user: User = Depends(get_current_user)):
    get_parent(db, sub_service_id, include_inactive=False)
    if db.scalar(select(ServicePackage).where(ServicePackage.sub_service_id == sub_service_id, ServicePackage.slug == data.slug)):
        raise HTTPException(status_code=409, detail=f"Package slug '{data.slug}' already exists for this sub-service")
    package = ServicePackage(sub_service_id=sub_service_id, **data.model_dump())
    db.add(package)
    commit_catalog(db)
    db.refresh(package)
    write_audit_log(db, action="package.create", entity_type="ServicePackage", entity_id=package.id, user=user, request=request, new_value=model_snapshot(package))
    db.commit()
    return package


@router.patch("/{package_id}", response_model=ServicePackageRead, dependencies=manage)
def update_package(sub_service_id: int, package_id: int, data: ServicePackageUpdate, db: DbSession, request: Request, user: User = Depends(get_current_user)):
    package = get_package(db, sub_service_id, package_id)
    old = model_snapshot(package)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(package, field, value)
    write_audit_log(db, action="package.update", entity_type="ServicePackage", entity_id=package.id, user=user, request=request, old_value=old, new_value=model_snapshot(package))
    commit_catalog(db)
    db.refresh(package)
    return package


@router.delete("/{package_id}", dependencies=manage)
def delete_package(sub_service_id: int, package_id: int, db: DbSession, request: Request, user: User = Depends(get_current_user)):
    package = get_package(db, sub_service_id, package_id)
    write_audit_log(db, action="package.delete", entity_type="ServicePackage", entity_id=package.id, user=user, request=request, old_value=model_snapshot(package))
    db.delete(package)
    commit_catalog(db)
    return {"message": "Package deleted"}
