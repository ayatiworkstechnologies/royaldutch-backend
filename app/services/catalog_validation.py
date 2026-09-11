from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.category import Category
from app.models.enums import RecordStatus
from app.models.staff import Staff


def validate_catalog_values(db, model, values, record_id=None):
    required = ("name", "slug", "status")
    if model is not Category:
        required += ("category_id", "currency")
    for field in required:
        if field in values and (values[field] is None or values[field] == ""):
            raise HTTPException(status_code=422, detail=f"{field} cannot be empty")
    unique_fields = ("external_id", "slug", "name") if model is Category else ("external_id", "slug")
    for field in unique_fields:
        if values.get(field) is None:
            continue
        query = select(model.id).where(getattr(model, field) == values[field])
        if record_id is not None:
            query = query.where(model.id != record_id)
        if db.scalar(query) is not None:
            raise HTTPException(status_code=409, detail=f"{model.__name__} with this {field} already exists")
    if "category_id" in values:
        category = db.get(Category, values["category_id"])
        if category is None:
            raise HTTPException(status_code=422, detail="Invalid category_id: use the category's database id, not external_id")
        if category.status != RecordStatus.active:
            raise HTTPException(status_code=422, detail="Services can only be assigned to an active category")


def resolve_staff(db, staff_ids):
    staff = list(db.scalars(select(Staff).where(Staff.id.in_(staff_ids))).all())
    missing = sorted(set(staff_ids) - {member.id for member in staff})
    if missing:
        raise HTTPException(status_code=422, detail=f"Invalid staff_ids: {missing}")
    return staff


def commit_catalog(db):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Catalog values conflict with an existing record or referenced ID") from exc
