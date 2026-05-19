from fastapi import APIRouter, Depends

from app.api.deps import DbSession, get_current_admin
from app.schemas.dashboard import DashboardStats
from app.services.booking_service import dashboard_stats

router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_admin)])


@router.get("", response_model=DashboardStats)
def get_dashboard(db: DbSession) -> dict:
    return dashboard_stats(db)
