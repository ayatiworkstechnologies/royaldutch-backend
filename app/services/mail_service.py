from app.models.booking import Booking
from app.models.enums import BookingStatus, MailStatus
from app.models.mail import MailMessage


def patient_email(booking: Booking) -> str | None:
    return booking.patient.email if booking.patient and booking.patient.email else None


def format_date_time(booking: Booking) -> str:
    return f"{booking.booking_date} at {booking.booking_time.strftime('%H:%M')}"


def mail_text_for_booking(booking: Booking, template: str) -> tuple[str, str]:
    patient_name = booking.patient.full_name if booking.patient else "Patient"
    service_name = booking.service.name if booking.service else "your service"
    staff_name = booking.staff.name if booking.staff else "our specialist"
    when = format_date_time(booking)

    templates = {
        "created": (
            f"Appointment request received - {booking.booking_code}",
            f"Dear {patient_name},\n\nYour appointment request for {service_name} has been received.\nRequested time: {when}\nBooking code: {booking.booking_code}\n\nOur team will confirm your booking shortly.\n\nRoyal Dutch Medical Centre",
        ),
        "confirmed": (
            f"Appointment confirmed - {booking.booking_code}",
            f"Dear {patient_name},\n\nYour appointment for {service_name} is confirmed.\nDate and time: {when}\nSpecialist: {staff_name}\nBooking code: {booking.booking_code}\n\nRoyal Dutch Medical Centre",
        ),
        "cancelled": (
            f"Appointment cancelled - {booking.booking_code}",
            f"Dear {patient_name},\n\nYour appointment request for {service_name} has been cancelled.\nBooking code: {booking.booking_code}\n\nPlease contact us if you would like to reschedule.\n\nRoyal Dutch Medical Centre",
        ),
        "completed": (
            f"Thank you for visiting - {booking.booking_code}",
            f"Dear {patient_name},\n\nThank you for visiting Royal Dutch Medical Centre for {service_name}.\nBooking code: {booking.booking_code}\n\nWe look forward to seeing you again.",
        ),
        "reminder": (
            f"Appointment reminder - {booking.booking_code}",
            f"Dear {patient_name},\n\nThis is a reminder for your appointment.\nService: {service_name}\nDate and time: {when}\nSpecialist: {staff_name}\nBooking code: {booking.booking_code}\n\nRoyal Dutch Medical Centre",
        ),
    }
    return templates.get(template, templates["created"])


def create_booking_mail(booking: Booking, template: str, status: MailStatus = MailStatus.queued) -> MailMessage | None:
    email = patient_email(booking)
    if not email:
        return None

    subject, body = mail_text_for_booking(booking, template)
    return MailMessage(
        booking_id=booking.id,
        patient_id=booking.patient_id,
        recipient_email=email,
        cc_emails=None,
        bcc_emails=None,
        recipient_name=booking.patient.full_name if booking.patient else None,
        subject=subject,
        body=body,
        status=status,
    )


def template_for_status(status: BookingStatus) -> str | None:
    return {
        BookingStatus.confirmed: "confirmed",
        BookingStatus.cancelled: "cancelled",
        BookingStatus.completed: "completed",
    }.get(status)
