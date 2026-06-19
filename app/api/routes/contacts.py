from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.permissions import require_permission
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactRead, ContactUpdate
from app.services.management_alert_service import send_contact_alerts

router = APIRouter(prefix="/contacts", tags=["contacts"])

_auth = Depends(require_permission("bookings.read"))


@router.get("", response_model=list[ContactRead], dependencies=[_auth])
def list_contacts(
    db: DbSession,
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
) -> list[ContactRead]:
    query = select(Contact).order_by(Contact.created_at.desc())
    if status:
        query = query.where(Contact.status == status)
    if search:
        like = f"%{search}%"
        query = query.where(
            Contact.full_name.ilike(like) | Contact.phone.ilike(like) | Contact.email.ilike(like)
        )
    return list(db.scalars(query).all())


@router.post("", response_model=ContactRead)
def create_contact(data: ContactCreate, db: DbSession) -> ContactRead:
    contact = Contact(**data.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    send_contact_alerts(contact, db)
    db.commit()
    return contact


@router.patch("/{contact_id}", response_model=ContactRead, dependencies=[_auth])
def update_contact(contact_id: int, data: ContactUpdate, db: DbSession) -> ContactRead:
    contact = db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}", dependencies=[_auth])
def delete_contact(contact_id: int, db: DbSession) -> dict:
    contact = db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(contact)
    db.commit()
    return {"message": "Contact deleted"}
