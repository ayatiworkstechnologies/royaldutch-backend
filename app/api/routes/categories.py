from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select

from app.api.deps import DbSession, get_current_admin
from app.models.category import Category
from app.models.enums import RecordStatus
from app.models.service import Service
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate

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


@router.post("", response_model=CategoryRead, dependencies=[Depends(get_current_admin)])
def create_category(data: CategoryCreate, db: DbSession) -> Category:
    category = Category(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/{category_id}", response_model=CategoryRead, dependencies=[Depends(get_current_admin)])
def update_category(category_id: int, data: CategoryUpdate, db: DbSession) -> Category:
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", dependencies=[Depends(get_current_admin)])
def delete_category(category_id: int, db: DbSession) -> dict:
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    service_count = db.scalar(select(func.count()).select_from(Service).where(Service.category_id == category.id))
    if service_count:
        category.status = RecordStatus.inactive
        db.query(Service).filter(Service.category_id == category.id).update(
            {Service.status: RecordStatus.inactive},
            synchronize_session=False,
        )
        db.commit()
        return {"message": "Category has services and was marked inactive"}
    db.delete(category)
    db.commit()
    return {"message": "Category deleted"}
