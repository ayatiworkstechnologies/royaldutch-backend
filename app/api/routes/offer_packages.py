from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession, get_current_user
from app.core.permissions import require_permission
from app.core.config import get_settings
from app.models.enums import RecordStatus
from app.models.booking import Booking
from app.models.offer_package import OfferPackage
from app.models.service import Service
from app.models.user import User
from app.schemas.offer_package import OfferPackageCreate, OfferPackageRead, OfferPackageUpdate
from app.services.audit_service import model_snapshot, write_audit_log


router = APIRouter(prefix="/offer-packages", tags=["offer packages"])
admin_router = APIRouter(
    prefix="/admin/offer-packages",
    tags=["offer packages"],
    dependencies=[Depends(require_permission("services.manage"))],
)

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def image_storage_dir() -> Path:
    directory = Path(get_settings().offer_package_image_storage_dir).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def offer_query():
    return select(OfferPackage).options(joinedload(OfferPackage.service))


def require_service(db: DbSession, service_id: int) -> Service:
    service = db.get(Service, service_id)
    if not service or service.status != RecordStatus.active:
        raise HTTPException(status_code=404, detail="Booking service not found or inactive")
    return service


def validate_prices(original_price, offer_price) -> None:
    if offer_price >= original_price:
        raise HTTPException(status_code=422, detail="Offer price must be lower than original price")


@router.get("", response_model=list[OfferPackageRead])
def list_public_offers(db: DbSession):
    query = offer_query().where(OfferPackage.status == RecordStatus.active).order_by(OfferPackage.id)
    return list(db.scalars(query).unique().all())


@router.get("/images/{file_name}", include_in_schema=False)
def get_offer_image(file_name: str):
    safe_name = Path(file_name).name
    if safe_name != file_name:
        raise HTTPException(status_code=404, detail="Image not found")
    path = image_storage_dir() / safe_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)


@router.get("/{offer_id}", response_model=OfferPackageRead)
def get_public_offer(offer_id: int, db: DbSession):
    offer = db.scalar(offer_query().where(OfferPackage.id == offer_id, OfferPackage.status == RecordStatus.active))
    if not offer:
        raise HTTPException(status_code=404, detail="Offer package not found")
    return offer


@admin_router.get("", response_model=list[OfferPackageRead])
def list_admin_offers(db: DbSession):
    return list(db.scalars(offer_query().order_by(OfferPackage.id)).unique().all())


@admin_router.post("/image")
async def upload_offer_image(image: UploadFile = File(...)):
    extension = ALLOWED_IMAGE_TYPES.get(image.content_type or "")
    if not extension:
        raise HTTPException(status_code=422, detail="Upload a PNG, JPEG, or WebP image")
    content = await image.read(MAX_IMAGE_BYTES + 1)
    if not content:
        raise HTTPException(status_code=422, detail="Image file is empty")
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be 5 MB or smaller")
    file_name = f"{uuid4().hex}{extension}"
    (image_storage_dir() / file_name).write_bytes(content)
    return {"image_url": f"/api/offer-packages/images/{file_name}"}


@admin_router.post("", response_model=OfferPackageRead, status_code=201)
def create_offer(data: OfferPackageCreate, db: DbSession, request: Request, user: User = Depends(get_current_user)):
    service = require_service(db, data.service_id)
    if data.currency != service.currency:
        raise HTTPException(status_code=422, detail="Offer currency must match the booking service currency")
    offer = OfferPackage(**data.model_dump())
    db.add(offer)
    db.flush()
    write_audit_log(db, action="offer_package.create", entity_type="OfferPackage", entity_id=offer.id, user=user, request=request, new_value=model_snapshot(offer))
    db.commit()
    return db.scalar(offer_query().where(OfferPackage.id == offer.id))


@admin_router.patch("/{offer_id}", response_model=OfferPackageRead)
def update_offer(offer_id: int, data: OfferPackageUpdate, db: DbSession, request: Request, user: User = Depends(get_current_user)):
    offer = db.get(OfferPackage, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer package not found")
    old = model_snapshot(offer)
    values = data.model_dump(exclude_unset=True)
    service = require_service(db, values.get("service_id", offer.service_id))
    original_price = values.get("original_price", offer.original_price)
    offer_price = values.get("offer_price", offer.offer_price)
    validate_prices(original_price, offer_price)
    if values.get("currency", offer.currency) != service.currency:
        raise HTTPException(status_code=422, detail="Offer currency must match the booking service currency")
    for field, value in values.items():
        setattr(offer, field, value)
    write_audit_log(db, action="offer_package.update", entity_type="OfferPackage", entity_id=offer.id, user=user, request=request, old_value=old, new_value=model_snapshot(offer))
    db.commit()
    return db.scalar(offer_query().where(OfferPackage.id == offer.id))


@admin_router.delete("/{offer_id}")
def delete_offer(offer_id: int, db: DbSession, request: Request, user: User = Depends(get_current_user)):
    offer = db.get(OfferPackage, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer package not found")
    old = model_snapshot(offer)
    booking_count = db.scalar(
        select(func.count()).select_from(Booking).where(Booking.offer_package_id == offer.id)
    )
    if booking_count:
        # Preserve historical booking data but remove the offer from the public site.
        offer.status = RecordStatus.inactive
        message = "Offer package has bookings and was archived"
    else:
        db.delete(offer)
        message = "Offer package deleted"
    write_audit_log(db, action="offer_package.delete", entity_type="OfferPackage", entity_id=offer.id, user=user, request=request, old_value=old, new_value=model_snapshot(offer))
    db.commit()
    return {"message": message}
