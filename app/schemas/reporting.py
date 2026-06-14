from decimal import Decimal

from app.schemas.common import ORMModel


class ReportingSummary(ORMModel):
    date_from: str | None
    date_to: str | None
    bookings_by_status: dict[str, int]
    revenue: dict[str, Decimal]
    top_services: list[dict]
    new_patients: int


class OperationalReport(ORMModel):
    bookings_by_day: list[dict]
    staff_utilization: list[dict]
    payment_mix: list[dict]
