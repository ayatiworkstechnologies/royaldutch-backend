from string import Formatter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.email_template import EmailTemplate
from app.models.enums import RecordStatus


DEFAULT_EMAIL_TEMPLATES = [
    {
        "name": "Booking Request Received",
        "slug": "created",
        "description": "Queued when a patient submits an appointment request.",
        "subject": "Appointment request received - {booking_code}",
        "body": (
            "Dear {patient_name},\n\n"
            "Your appointment request for {service_name} has been received.\n"
            "Requested time: {appointment_time}\n"
            "Booking code: {booking_code}\n\n"
            "Our team will confirm your booking shortly.\n\n"
            "Royal Dutch Medical Centre"
        ),
    },
    {
        "name": "Booking Confirmed",
        "slug": "confirmed",
        "description": "Sent when admin confirms the appointment.",
        "subject": "Appointment confirmed - {booking_code}",
        "body": (
            "Dear {patient_name},\n\n"
            "Your appointment for {service_name} is confirmed.\n"
            "Date and time: {appointment_time}\n"
            "Specialist: {staff_name}\n"
            "Booking code: {booking_code}\n\n"
            "Royal Dutch Medical Centre"
        ),
    },
    {
        "name": "Booking Cancelled",
        "slug": "cancelled",
        "description": "Sent when an appointment is cancelled.",
        "subject": "Appointment cancelled - {booking_code}",
        "body": (
            "Dear {patient_name},\n\n"
            "Your appointment request for {service_name} has been cancelled.\n"
            "Booking code: {booking_code}\n\n"
            "Please contact us if you would like to reschedule.\n\n"
            "Royal Dutch Medical Centre"
        ),
    },
    {
        "name": "Visit Completed",
        "slug": "completed",
        "description": "Sent after a visit is completed.",
        "subject": "Thank you for visiting - {booking_code}",
        "body": (
            "Dear {patient_name},\n\n"
            "Thank you for visiting Royal Dutch Medical Centre for {service_name}.\n"
            "Booking code: {booking_code}\n\n"
            "We look forward to seeing you again."
        ),
    },
    {
        "name": "Appointment Reminder",
        "slug": "reminder",
        "description": "Manual reminder before an appointment.",
        "subject": "Appointment reminder - {booking_code}",
        "body": (
            "Dear {patient_name},\n\n"
            "This is a reminder for your appointment.\n"
            "Service: {service_name}\n"
            "Date and time: {appointment_time}\n"
            "Specialist: {staff_name}\n"
            "Booking code: {booking_code}\n\n"
            "Royal Dutch Medical Centre"
        ),
    },
    {
        "name": "Payment Received",
        "slug": "payment_received",
        "description": "Manual payment confirmation email.",
        "subject": "Payment received - Royal Dutch Medical Centre",
        "body": (
            "Dear {patient_name},\n\n"
            "Thank you. Your payment has been received and updated in your account.\n\n"
            "Royal Dutch Medical Centre"
        ),
    },
]


def seed_default_email_templates(db: Session) -> None:
    for item in DEFAULT_EMAIL_TEMPLATES:
        exists = db.scalar(select(EmailTemplate).where(EmailTemplate.slug == item["slug"]))
        if exists:
            continue
        db.add(EmailTemplate(**item, status=RecordStatus.active))
    db.commit()


def booking_context(booking: Booking) -> dict[str, str]:
    patient = booking.patient
    service = booking.service
    staff = booking.staff
    return {
        "patient_name": patient.full_name if patient else "Patient",
        "patient_email": patient.email if patient and patient.email else "",
        "patient_phone": patient.phone if patient and patient.phone else "",
        "service_name": service.name if service else "your service",
        "staff_name": staff.name if staff else "our specialist",
        "booking_code": booking.booking_code,
        "booking_date": str(booking.booking_date),
        "booking_time": booking.booking_time.strftime("%H:%M"),
        "appointment_time": f"{booking.booking_date} at {booking.booking_time.strftime('%H:%M')}",
        "clinic_name": "Royal Dutch Medical Centre",
    }


def render_text(template: str, context: dict[str, str]) -> str:
    allowed_keys = {field_name for _, field_name, _, _ in Formatter().parse(template) if field_name}
    safe_context = {key: context.get(key, "") for key in allowed_keys}
    return template.format(**safe_context)


def render_email_template(template: EmailTemplate, context: dict[str, str]) -> tuple[str, str]:
    return render_text(template.subject, context), render_text(template.body, context)


def fallback_template(slug: str) -> EmailTemplate:
    item = next((template for template in DEFAULT_EMAIL_TEMPLATES if template["slug"] == slug), DEFAULT_EMAIL_TEMPLATES[0])
    return EmailTemplate(**item, status=RecordStatus.active)


def get_active_template(db: Session | None, slug: str) -> EmailTemplate:
    if db:
        template = db.scalar(
            select(EmailTemplate).where(EmailTemplate.slug == slug, EmailTemplate.status == RecordStatus.active)
        )
        if template:
            return template
    return fallback_template(slug)
