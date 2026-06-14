from fastapi import APIRouter, Depends, Request

from app.api.deps import DbSession, get_current_user
from app.core.permissions import require_permission
from app.models.user import User
from app.schemas.setting import ClinicSettingsRead, ClinicSettingsUpdate
from app.services.audit_service import write_audit_log
from app.services.settings_service import get_clinic_settings, update_clinic_settings

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(require_permission("settings.manage"))])


@router.get("", response_model=ClinicSettingsRead)
def read_settings(db: DbSession) -> dict[str, str]:
    return get_clinic_settings(db)


@router.patch("", response_model=ClinicSettingsRead)
def patch_settings(data: ClinicSettingsUpdate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> dict[str, str]:
    old_value = get_clinic_settings(db)
    updated = update_clinic_settings(db, data)
    write_audit_log(db, action="settings.update", entity_type="ClinicSetting", user=user, request=request, old_value=old_value, new_value=updated)
    db.commit()
    return updated
