from fastapi import APIRouter, Depends

from app.api.deps import DbSession, get_current_admin
from app.schemas.setting import ClinicSettingsRead, ClinicSettingsUpdate
from app.services.settings_service import get_clinic_settings, update_clinic_settings

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(get_current_admin)])


@router.get("", response_model=ClinicSettingsRead)
def read_settings(db: DbSession) -> dict[str, str]:
    return get_clinic_settings(db)


@router.patch("", response_model=ClinicSettingsRead)
def patch_settings(data: ClinicSettingsUpdate, db: DbSession) -> dict[str, str]:
    return update_clinic_settings(db, data)
