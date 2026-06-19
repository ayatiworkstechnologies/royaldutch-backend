from decimal import Decimal

from app.schemas.common import ORMModel


class DashboardStats(ORMModel):
    todays_bookings: int
    pending_bookings: int
    confirmed_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    no_show_bookings: int = 0
    total_patients: int = 0
    total_revenue: Decimal
    booking_revenue: Decimal = Decimal("0")
    invoice_revenue: Decimal = Decimal("0")
    collected_revenue: Decimal = Decimal("0")
    refunded_revenue: Decimal = Decimal("0")
    net_revenue: Decimal = Decimal("0")
    most_booked_services: list[dict]
    recent_bookings: list[dict] = []
