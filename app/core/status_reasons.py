from app.models.enums import BookingStatus

BOOKING_STATUS_REASONS: dict[BookingStatus, list[str]] = {
    BookingStatus.confirmed: [
        "Doctor available",
        "Patient reconfirmed",
        "Rescheduled and reconfirmed",
    ],
    BookingStatus.completed: [
        "Treatment completed",
        "Follow-up scheduled",
        "Patient discharged",
    ],
    BookingStatus.cancelled: [
        "Patient request",
        "Doctor unavailable",
        "No response from patient",
        "Duplicate booking",
        "Other",
    ],
    BookingStatus.no_show: [
        "Patient did not arrive",
        "Late cancellation",
        "Other",
    ],
    BookingStatus.rescheduled: [
        "Patient requested new time",
        "Doctor unavailable",
        "Clinic closure",
        "Other",
    ],
}


def is_valid_reason(status_value: BookingStatus, reason: str) -> bool:
    return reason in BOOKING_STATUS_REASONS.get(status_value, [])
