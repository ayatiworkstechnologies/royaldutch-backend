from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select

from app.api.deps import DbSession, get_current_user
from app.core.permissions import require_permission
from app.models.category import Category
from app.models.enums import RecordStatus
from app.models.service import Service
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.services.audit_service import model_snapshot, write_audit_log

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
def list_categories(
    db: DbSession,
    include_inactive: bool = Query(default=False),
) -> list[Category]:
    query = select(Category).order_by(Category.external_id, Category.name)
    if not include_inactive:
        query = query.where(Category.status == RecordStatus.active)
    return list(db.scalars(query).all())


@router.post("", response_model=CategoryRead, dependencies=[Depends(require_permission("categories.manage"))])
def create_category(data: CategoryCreate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> Category:
    category = Category(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    write_audit_log(db, action="category.create", entity_type="Category", entity_id=category.id, user=user, request=request, new_value=model_snapshot(category))
    db.commit()
    return category


@router.patch("/{category_id}", response_model=CategoryRead, dependencies=[Depends(require_permission("categories.manage"))])
def update_category(category_id: int, data: CategoryUpdate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> Category:
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    old_value = model_snapshot(category)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    write_audit_log(db, action="category.update", entity_type="Category", entity_id=category.id, user=user, request=request, old_value=old_value, new_value=model_snapshot(category))
    db.commit()
    return category


@router.delete("/{category_id}", dependencies=[Depends(require_permission("categories.manage"))])
def delete_category(category_id: int, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> dict:
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    old_value = model_snapshot(category)
    service_count = db.scalar(select(func.count()).select_from(Service).where(Service.category_id == category.id))
    if service_count:
        category.status = RecordStatus.inactive
        db.query(Service).filter(Service.category_id == category.id).update(
            {Service.status: RecordStatus.inactive},
            synchronize_session=False,
        )
        write_audit_log(db, action="category.delete", entity_type="Category", entity_id=category.id, user=user, request=request, old_value=old_value, new_value=model_snapshot(category))
        db.commit()
        return {"message": "Category has services and was marked inactive"}
    db.delete(category)
    write_audit_log(db, action="category.delete", entity_type="Category", entity_id=category_id, user=user, request=request, old_value=old_value)
    db.commit()
    return {"message": "Category deleted"}
