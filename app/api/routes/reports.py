from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession
from app.core.permissions import require_permission
from app.schemas.reporting import OperationalReport, ReportingSummary
from app.services.reporting_service import operational_report, reporting_summary

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(require_permission("reports.read"))])


@router.get("/summary", response_model=ReportingSummary)
def summary_report(db: DbSession, date_from: date | None = Query(default=None), date_to: date | None = Query(default=None)) -> dict:
    return reporting_summary(db, date_from, date_to)


@router.get("/operations", response_model=OperationalReport)
def operations_report(db: DbSession, date_from: date | None = Query(default=None), date_to: date | None = Query(default=None)) -> dict:
    return operational_report(db, date_from, date_to)
