from fastapi import APIRouter, Depends

from app.api.deps import DbSession
from app.core.permissions import require_permission
from app.schemas.dashboard import DashboardStats
from app.services.booking_service import dashboard_stats

router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(require_permission("dashboard.read"))])


@router.get("", response_model=DashboardStats)
def get_dashboard(db: DbSession) -> dict:
    return dashboard_stats(db)
