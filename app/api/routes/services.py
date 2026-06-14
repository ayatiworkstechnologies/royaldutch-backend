from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession, get_current_user
from app.core.permissions import require_permission
from app.models.booking import Booking
from app.models.category import Category
from app.models.enums import RecordStatus
from app.models.service import Service
from app.models.staff import Staff
from app.models.user import User
from app.schemas.service import ServiceCreate, ServiceRead, ServiceUpdate
from app.services.audit_service import model_snapshot, write_audit_log

router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=list[ServiceRead])
def list_services(
    db: DbSession,
    category_slug: str | None = Query(default=None),
    include_inactive: bool = Query(default=False),
) -> list[Service]:
    query = select(Service).options(joinedload(Service.category)).order_by(Service.external_id, Service.name)
    if not include_inactive:
        query = query.where(Service.status == RecordStatus.active)
    if category_slug:
        query = query.join(Service.category).where(Category.slug == category_slug)
        if not include_inactive:
            query = query.where(Category.status == RecordStatus.active)
    return list(db.scalars(query).unique().all())


@router.get("/{service_slug}", response_model=ServiceRead)
def get_service(service_slug: str, db: DbSession) -> Service:
    service = db.scalar(select(Service).where(Service.slug == service_slug, Service.status == RecordStatus.active))
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


@router.post("", response_model=ServiceRead, dependencies=[Depends(require_permission("services.manage"))])
def create_service(data: ServiceCreate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> Service:
    staff_ids = data.staff_ids
    service = Service(**data.model_dump(exclude={"staff_ids"}))
    if staff_ids:
        service.staff = list(db.scalars(select(Staff).where(Staff.id.in_(staff_ids))).all())
    db.add(service)
    db.commit()
    db.refresh(service)
    write_audit_log(db, action="service.create", entity_type="Service", entity_id=service.id, user=user, request=request, new_value=model_snapshot(service))
    db.commit()
    return service


@router.patch("/{service_id}", response_model=ServiceRead, dependencies=[Depends(require_permission("services.manage"))])
def update_service(service_id: int, data: ServiceUpdate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> Service:
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    old_value = model_snapshot(service)
    update_data = data.model_dump(exclude_unset=True)
    staff_ids = update_data.pop("staff_ids", None)
    for field, value in update_data.items():
        setattr(service, field, value)
    if staff_ids is not None:
        service.staff = list(db.scalars(select(Staff).where(Staff.id.in_(staff_ids))).all())
    db.commit()
    db.refresh(service)
    write_audit_log(db, action="service.update", entity_type="Service", entity_id=service.id, user=user, request=request, old_value=old_value, new_value=model_snapshot(service))
    db.commit()
    return service


@router.delete("/{service_id}", dependencies=[Depends(require_permission("services.manage"))])
def delete_service(service_id: int, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> dict:
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    old_value = model_snapshot(service)
    booking_count = db.scalar(select(func.count()).select_from(Booking).where(Booking.service_id == service.id))
    if booking_count:
        service.status = RecordStatus.inactive
        write_audit_log(db, action="service.delete", entity_type="Service", entity_id=service.id, user=user, request=request, old_value=old_value, new_value=model_snapshot(service))
        db.commit()
        return {"message": "Service has bookings and was marked inactive"}
    db.delete(service)
    write_audit_log(db, action="service.delete", entity_type="Service", entity_id=service_id, user=user, request=request, old_value=old_value)
    db.commit()
    return {"message": "Service deleted"}
