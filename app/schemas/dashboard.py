from decimal import Decimal

from app.schemas.common import ORMModel


class DashboardStats(ORMModel):
    todays_bookings: int
    pending_bookings: int
    confirmed_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    total_revenue: Decimal
    most_booked_services: list[dict]
