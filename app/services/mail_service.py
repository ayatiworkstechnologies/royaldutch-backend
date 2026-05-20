from app.models.booking import Booking
from app.models.enums import BookingStatus, MailStatus
from app.models.mail import MailMessage
from app.services.email_template_service import booking_context, get_active_template, render_email_template


def patient_email(booking: Booking) -> str | None:
    return booking.patient.email if booking.patient and booking.patient.email else None


def format_date_time(booking: Booking) -> str:
    return f"{booking.booking_date} at {booking.booking_time.strftime('%H:%M')}"


def mail_text_for_booking(booking: Booking, template: str, db=None) -> tuple[str, str]:
    email_template = get_active_template(db, template)
    return render_email_template(email_template, booking_context(booking))


def create_booking_mail(booking: Booking, template: str, status: MailStatus = MailStatus.queued, db=None) -> MailMessage | None:
    email = patient_email(booking)
    if not email:
        return None

    subject, body = mail_text_for_booking(booking, template, db)
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
