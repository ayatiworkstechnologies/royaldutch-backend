from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession, get_current_admin
from app.models.booking import Booking
from app.models.enums import RecordStatus
from app.models.service import Service
from app.models.staff import Staff, StaffAvailability
from app.schemas.staff import StaffCreate, StaffRead, StaffUpdate

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


@router.post("", response_model=StaffRead, dependencies=[Depends(get_current_admin)])
def create_staff(data: StaffCreate, db: DbSession) -> StaffRead:
    staff = Staff(**data.model_dump(exclude={"service_ids", "availability"}))
    staff.services = list(db.scalars(select(Service).where(Service.id.in_(data.service_ids))).all())
    staff.availability = [StaffAvailability(**item.model_dump()) for item in data.availability]
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return serialize_staff(staff)


@router.patch("/{staff_id}", response_model=StaffRead, dependencies=[Depends(get_current_admin)])
def update_staff(staff_id: int, data: StaffUpdate, db: DbSession) -> StaffRead:
    staff = db.scalar(
        select(Staff).where(Staff.id == staff_id).options(joinedload(Staff.services), joinedload(Staff.availability))
    )
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
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
    return serialize_staff(staff)


@router.delete("/{staff_id}", dependencies=[Depends(get_current_admin)])
def delete_staff(staff_id: int, db: DbSession) -> dict:
    staff = db.get(Staff, staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    booking_count = db.scalar(select(func.count()).select_from(Booking).where(Booking.staff_id == staff.id))
    if booking_count:
        staff.status = RecordStatus.inactive
        db.commit()
        return {"message": "Staff has bookings and was marked inactive"}
    db.delete(staff)
    db.commit()
    return {"message": "Staff deleted"}
