from html import escape
from string import Formatter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.billing import Invoice
from app.models.booking import Booking
from app.models.email_template import EmailTemplate
from app.models.enums import RecordStatus
from app.models.payment import Payment
from app.services.settings_service import get_clinic_settings


def detail_rows(rows: list[tuple[str, str]]) -> str:
    return "".join(
        f"""
        <tr>
          <td style="padding:13px 0;color:#64748b;font-size:14px;border-bottom:1px solid #ead8e6;">{label}</td>
          <td style="padding:13px 0;color:#24101f;font-size:14px;font-weight:700;text-align:right;border-bottom:1px solid #ead8e6;">{value}</td>
        </tr>
        """
        for label, value in rows
    )


def email_body(title: str, intro: str, rows: list[tuple[str, str]], note: str) -> str:
    details = detail_rows(rows)
    return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
  </head>
  <body style="margin:0;padding:0;background:#fcfafc;font-family:Arial,Helvetica,sans-serif;color:#24101f;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#fcfafc;margin:0;padding:32px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;background:#ffffff;border-radius:18px;overflow:hidden;border:1px solid #ead8e6;box-shadow:0 18px 45px rgba(91,15,77,0.12);">
            <tr>
              <td style="background:#5b0f4d;padding:0;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#5b0f4d;">
                  <tr>
                    <td style="padding:8px 32px;background:#38072e;"></td>
                  </tr>
                  <tr>
                    <td style="padding:28px 32px 30px;">
                      <div style="font-size:12px;letter-spacing:2px;text-transform:uppercase;color:#f5d0fe;font-weight:700;">Royal Dutch Medical Centre</div>
                      <h1 style="margin:10px 0 0;color:#ffffff;font-size:26px;line-height:1.25;font-weight:800;">{title}</h1>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:32px;">
                <p style="margin:0 0 18px;color:#3f2739;font-size:16px;line-height:1.7;">Dear {{patient_name}},</p>
                <p style="margin:0 0 24px;color:#3f2739;font-size:16px;line-height:1.7;">{intro}</p>
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#fff7fd;border:1px solid #ead8e6;border-radius:14px;padding:6px 18px;margin:0 0 24px;">
                  {details}
                </table>
                <p style="margin:0;color:#3f2739;font-size:15px;line-height:1.7;">{note}</p>
              </td>
            </tr>
            <tr>
              <td style="padding:24px 32px;background:#24101f;">
                <p style="margin:0 0 8px;color:#ffffff;font-size:15px;font-weight:700;">{{clinic_name}}</p>
                <p style="margin:0;color:#ead8e6;font-size:13px;line-height:1.6;">This is an automated message from our clinic system. If you need help with your booking, invoice, or payment, please contact our reception team.</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


DEFAULT_EMAIL_TEMPLATES = [
    {
        "name": "Booking Request Received",
        "slug": "created",
        "description": "Queued when a patient submits an appointment request.",
        "subject": "We received your appointment request - {booking_code}",
        "body": email_body(
            "Appointment request received",
            "Thank you for choosing {clinic_name}. We have received your request and our team is reviewing the details.",
            [
                ("Service", "{service_name}"),
                ("Preferred time", "{appointment_time}"),
                ("Booking reference", "{booking_code}"),
            ],
            "You will receive another message as soon as your appointment is confirmed. If anything needs to be adjusted, our team will contact you directly.",
        ),
    },
    {
        "name": "Booking Confirmed",
        "slug": "confirmed",
        "description": "Sent when admin confirms the appointment.",
        "subject": "Your appointment is confirmed - {booking_code}",
        "body": email_body(
            "Appointment confirmed",
            "Your appointment at {clinic_name} is confirmed. We look forward to welcoming you.",
            [
                ("Service", "{service_name}"),
                ("Date and time", "{appointment_time}"),
                ("Specialist", "{staff_name}"),
                ("Booking reference", "{booking_code}"),
            ],
            "Please arrive a few minutes before your appointment time. If you need to reschedule, contact our team and we will be happy to help.",
        ),
    },
    {
        "name": "Booking Cancelled",
        "slug": "cancelled",
        "description": "Sent when an appointment is cancelled.",
        "subject": "Your appointment has been cancelled - {booking_code}",
        "body": email_body(
            "Appointment cancelled",
            "This message confirms that your appointment request has been cancelled.",
            [
                ("Service", "{service_name}"),
                ("Original time", "{appointment_time}"),
                ("Booking reference", "{booking_code}"),
            ],
            "If you would like to book another time, our team will be glad to assist you.",
        ),
    },
    {
        "name": "Visit Completed",
        "slug": "completed",
        "description": "Sent after a visit is completed.",
        "subject": "Thank you for visiting {clinic_name}",
        "body": email_body(
            "Thank you for visiting",
            "Thank you for visiting {clinic_name}. We hope your experience with our team was comfortable and reassuring.",
            [
                ("Service", "{service_name}"),
                ("Appointment time", "{appointment_time}"),
                ("Booking reference", "{booking_code}"),
            ],
            "If you have follow-up questions or need another appointment, please contact our clinic team.",
        ),
    },
    {
        "name": "Appointment Reminder",
        "slug": "reminder",
        "description": "Manual reminder before an appointment.",
        "subject": "Reminder: your appointment is coming up - {booking_code}",
        "body": email_body(
            "Appointment reminder",
            "This is a friendly reminder about your upcoming appointment at {clinic_name}.",
            [
                ("Service", "{service_name}"),
                ("Date and time", "{appointment_time}"),
                ("Specialist", "{staff_name}"),
                ("Booking reference", "{booking_code}"),
            ],
            "Please arrive a few minutes early. If your plans have changed, contact us so we can support you with a new time.",
        ),
    },
    {
        "name": "Payment Received",
        "slug": "payment_received",
        "description": "Queued when a customer payment is recorded.",
        "subject": "Payment received for invoice {invoice_number}",
        "body": email_body(
            "Payment received",
            "Thank you. Your payment has been received and recorded successfully.",
            [
                ("Invoice", "{invoice_number}"),
                ("Amount received", "{payment_amount} {currency}"),
                ("Payment method", "{payment_method}"),
                ("Transaction reference", "{transaction_id}"),
                ("Remaining balance", "{balance_due} {currency}"),
            ],
            "If you have any questions about this payment, please contact our billing team.",
        ),
    },
    {
        "name": "Invoice Issued",
        "slug": "invoice_issued",
        "description": "Queued when an invoice is ready to send to the customer.",
        "subject": "Your invoice from {clinic_name} - {invoice_number}",
        "body": email_body(
            "Invoice ready",
            "Your invoice from {clinic_name} is ready. Please find the billing summary below.",
            [
                ("Invoice number", "{invoice_number}"),
                ("Service", "{service_name}"),
                ("Issue date", "{issue_date}"),
                ("Due date", "{due_date}"),
                ("Subtotal", "{subtotal} {currency}"),
                ("Discount", "{discount_amount} {currency}"),
                ("Tax", "{tax_amount} {currency}"),
                ("Total", "{total_amount} {currency}"),
                ("Paid", "{paid_amount} {currency}"),
                ("Balance due", "{balance_due} {currency}"),
            ],
            "If payment has already been made, kindly disregard the balance line. For billing support, our team is ready to help.",
        ),
    },
]


def seed_default_email_templates(db: Session) -> None:
    for item in DEFAULT_EMAIL_TEMPLATES:
        exists = db.scalar(select(EmailTemplate).where(EmailTemplate.slug == item["slug"]))
        if exists:
            for field, value in item.items():
                setattr(exists, field, value)
            exists.status = RecordStatus.active
            continue
        db.add(EmailTemplate(**item, status=RecordStatus.active))
    db.commit()


def booking_context(booking: Booking, db: Session | None = None) -> dict[str, str]:
    settings = get_clinic_settings(db)
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
        "clinic_name": settings["clinic_name"],
        "clinic_email": settings["clinic_email"],
        "clinic_phone": settings["clinic_phone"],
        "clinic_address": settings["clinic_address"],
    }


def invoice_context(invoice: Invoice, db: Session | None = None) -> dict[str, str]:
    settings = get_clinic_settings(db)
    patient = invoice.patient or (invoice.booking.patient if invoice.booking else None)
    booking = invoice.booking
    service = booking.service if booking else None
    return {
        "patient_name": patient.full_name if patient else "Patient",
        "patient_email": patient.email if patient and patient.email else "",
        "patient_phone": patient.phone if patient and patient.phone else "",
        "service_name": service.name if service else "clinic service",
        "booking_code": booking.booking_code if booking else "",
        "invoice_number": invoice.invoice_number,
        "issue_date": str(invoice.issue_date),
        "due_date": str(invoice.due_date) if invoice.due_date else "",
        "subtotal": f"{invoice.subtotal:.2f}",
        "discount_amount": f"{invoice.discount_amount:.2f}",
        "tax_amount": f"{invoice.tax_amount:.2f}",
        "total_amount": f"{invoice.total_amount:.2f}",
        "paid_amount": f"{invoice.paid_amount:.2f}",
        "balance_due": f"{invoice.balance_due:.2f}",
        "currency": invoice.currency,
        "clinic_name": settings["clinic_name"],
        "clinic_email": settings["clinic_email"],
        "clinic_phone": settings["clinic_phone"],
        "clinic_address": settings["clinic_address"],
        "invoice_footer": settings["invoice_footer"],
        "invoice_terms": settings["invoice_terms"],
        "tax_registration_number": settings["tax_registration_number"],
    }


def payment_context(payment: Payment, db: Session | None = None) -> dict[str, str]:
    invoice = payment.invoice
    context = invoice_context(invoice, db) if invoice else {
        "patient_name": "Patient",
        "patient_email": "",
        "patient_phone": "",
        "service_name": "clinic service",
        "booking_code": "",
        "invoice_number": "",
        "issue_date": "",
        "due_date": "",
        "subtotal": "0.00",
        "discount_amount": "0.00",
        "tax_amount": "0.00",
        "total_amount": "0.00",
        "paid_amount": "0.00",
        "balance_due": "0.00",
        "currency": "AED",
        "clinic_name": "Royal Dutch Medical Centre",
        "clinic_email": "",
        "clinic_phone": "",
        "clinic_address": "",
        "invoice_footer": "",
        "invoice_terms": "",
        "tax_registration_number": "",
    }
    context.update(
        {
            "payment_amount": f"{payment.amount:.2f}",
            "payment_method": payment.payment_method,
            "payment_status": payment.payment_status,
            "transaction_id": payment.transaction_id or "",
        }
    )
    return context


def render_text(template: str, context: dict[str, str]) -> str:
    allowed_keys = {field_name for _, field_name, _, _ in Formatter().parse(template) if field_name}
    safe_context = {key: context.get(key, "") for key in allowed_keys}
    return template.format(**safe_context)


def render_email_template(template: EmailTemplate, context: dict[str, str]) -> tuple[str, str]:
    subject = render_text(template.subject, context)
    body_context = context
    if "<html" in template.body.lower():
        body_context = {key: escape(str(value), quote=True) for key, value in context.items()}
    return subject, render_text(template.body, body_context)


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
