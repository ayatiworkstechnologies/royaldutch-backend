from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession, get_current_user
from app.core.permissions import require_permission
from app.core.security import hash_password
from app.models.booking import Booking
from app.models.enums import RecordStatus, UserRole
from app.models.service import Service
from app.models.staff import Staff, StaffAvailability
from app.models.user import User
from app.schemas.staff import StaffCreate, StaffRead, StaffUpdate
from app.services.audit_service import model_snapshot, write_audit_log

router = APIRouter(prefix="/staff", tags=["staff"])


def serialize_staff(staff: Staff) -> StaffRead:
    data = StaffRead.model_validate(staff)
    data.service_ids = [service.id for service in staff.services]
    return data


@router.get("", response_model=list[StaffRead])
def list_staff(db: DbSession) -> list[StaffRead]:
    staff_members = db.scalars(
        select(Staff).options(joinedload(Staff.services), joinedload(Staff.availability)).order_by(Staff.name)
    ).unique().all()
    return [serialize_staff(staff) for staff in staff_members]


@router.post("", response_model=StaffRead, dependencies=[Depends(require_permission("staff.manage"))])
def create_staff(data: StaffCreate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> StaffRead:
    from datetime import time
    staff = Staff(**data.model_dump(exclude={"service_ids", "availability", "password"}))
    staff.services = list(db.scalars(select(Service).where(Service.id.in_(data.service_ids))).all())
    
    if data.availability:
        staff.availability = [StaffAvailability(**item.model_dump()) for item in data.availability]
    else:
        # Auto-assign Default Mon-Fri 9 AM to 5 PM
        staff.availability = [
            StaffAvailability(day_of_week=day, start_time=time(9, 0), end_time=time(17, 0))
            for day in range(5)
        ]
        
    db.add(staff)
    db.flush()  # get staff.id before linking

    if data.email:
        existing_user = db.scalar(select(User).where(User.email == data.email))
        if existing_user:
            existing_user.staff_id = staff.id
        elif data.password:
            role_val = data.role.lower()
            valid_roles = [r.value for r in UserRole]
            user_role = role_val if role_val in valid_roles else UserRole.doctor.value
            new_user = User(
                name=data.name,
                email=data.email,
                hashed_password=hash_password(data.password),
                role=user_role,
                staff_id=staff.id,
            )
            db.add(new_user)

    db.commit()
    db.refresh(staff)
    write_audit_log(db, action="staff.create", entity_type="Staff", entity_id=staff.id, user=user, request=request, new_value=model_snapshot(staff))
    db.commit()
    return serialize_staff(staff)


@router.patch("/{staff_id}", response_model=StaffRead, dependencies=[Depends(require_permission("staff.manage"))])
def update_staff(staff_id: int, data: StaffUpdate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> StaffRead:
    staff = db.scalar(
        select(Staff).where(Staff.id == staff_id).options(joinedload(Staff.services), joinedload(Staff.availability))
    )
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    old_value = model_snapshot(staff)
    update_data = data.model_dump(exclude_unset=True)
    service_ids = update_data.pop("service_ids", None)
    availability = update_data.pop("availability", None)
    for field, value in update_data.items():
        setattr(staff, field, value)
    if service_ids is not None:
        staff.services = list(db.scalars(select(Service).where(Service.id.in_(service_ids))).all())
    if availability is not None:
        staff.availability = [StaffAvailability(**item.model_dump()) for item in data.availability or []]
    db.commit()
    db.refresh(staff)
    write_audit_log(db, action="staff.update", entity_type="Staff", entity_id=staff.id, user=user, request=request, old_value=old_value, new_value=model_snapshot(staff))
    db.commit()
    return serialize_staff(staff)


@router.delete("/{staff_id}", dependencies=[Depends(require_permission("staff.manage"))])
def delete_staff(staff_id: int, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> dict:
    staff = db.get(Staff, staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    old_value = model_snapshot(staff)
    booking_count = db.scalar(select(func.count()).select_from(Booking).where(Booking.staff_id == staff.id))
    if booking_count:
        staff.status = RecordStatus.inactive
        write_audit_log(db, action="staff.delete", entity_type="Staff", entity_id=staff.id, user=user, request=request, old_value=old_value, new_value=model_snapshot(staff))
        db.commit()
        return {"message": "Staff has bookings and was marked inactive"}
    db.delete(staff)
    write_audit_log(db, action="staff.delete", entity_type="Staff", entity_id=staff_id, user=user, request=request, old_value=old_value)
    db.commit()
    return {"message": "Staff deleted"}
