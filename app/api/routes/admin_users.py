from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select

from app.api.deps import DbSession, get_current_user
from app.core.permissions import require_permission
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.admin_user import AdminUserCreate, AdminUserRead, AdminUserUpdate
from app.services.admin_user_service import ADMIN_MANAGED_ROLES, create_admin_user, update_admin_user
from app.services.audit_service import model_snapshot, write_audit_log
from app.utils.pagination import paginate_query

router = APIRouter(prefix="/admin/users", tags=["admin users"], dependencies=[Depends(require_permission("users.manage"))])


@router.get("", response_model=list[AdminUserRead])
def list_admin_users(db: DbSession, page: int | None = Query(default=None), limit: int | None = Query(default=None)):
    roles = [role.value for role in ADMIN_MANAGED_ROLES]
    query = select(User).where(User.role.in_(roles)).order_by(User.name)
    if page is not None and limit is not None:
        return paginate_query(db, query, page, limit)
    return list(db.scalars(query).all())


@router.post("", response_model=AdminUserRead)
def create_user(data: AdminUserCreate, db: DbSession, request: Request, current_user: User = Depends(get_current_user)) -> User:
    user = create_admin_user(db, data)
    write_audit_log(db, action="admin_user.create", entity_type="User", entity_id=user.id, user=current_user, request=request, new_value=model_snapshot(user))
    db.commit()
    return user


@router.patch("/{user_id}", response_model=AdminUserRead)
def patch_user(user_id: int, data: AdminUserUpdate, db: DbSession, request: Request, current_user: User = Depends(get_current_user)) -> User:
    user = db.get(User, user_id)
    if not user or user.role == UserRole.customer:
        raise HTTPException(status_code=404, detail="Admin user not found")
    old_value = model_snapshot(user)
    user = update_admin_user(db, user, data)
    write_audit_log(db, action="admin_user.update", entity_type="User", entity_id=user.id, user=current_user, request=request, old_value=old_value, new_value=model_snapshot(user))
    db.commit()
    return user


@router.delete("/{user_id}")
def deactivate_user(user_id: int, db: DbSession, request: Request, current_user: User = Depends(get_current_user)) -> dict:
    user = db.get(User, user_id)
    if not user or user.role == UserRole.customer:
        raise HTTPException(status_code=404, detail="Admin user not found")
    old_value = model_snapshot(user)
    user.is_active = False
    write_audit_log(db, action="admin_user.deactivate", entity_type="User", entity_id=user.id, user=current_user, request=request, old_value=old_value, new_value=model_snapshot(user))
    db.commit()
    return {"message": "Admin user deactivated"}
