"""
Send management alert + customer thank-you emails when a booking or contact
enquiry is submitted.  Emails are sent immediately via SMTP (not queued) and
saved to the mail_messages table for audit/visibility.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.contact import Contact
from app.models.enums import MailStatus
from app.models.mail import MailMessage
from app.services.settings_service import get_clinic_settings
from app.services.smtp_service import send_mail_message


# ── helpers ──────────────────────────────────────────────────────────────────

def _clinic_cfg(db: Session) -> tuple[str, str | None, str | None, str]:
    """Return (clinic_email, cc, bcc, clinic_name) from settings."""
    cfg = get_clinic_settings(db)
    return (
        cfg.get("clinic_email") or "",
        cfg.get("clinic_email_cc") or None,
        cfg.get("clinic_email_bcc") or None,
        cfg.get("clinic_name") or "Royal Dutch Medical Centre",
    )


def _alert_html(title: str, rows: list[tuple[str, str]], clinic_name: str) -> str:
    row_html = "".join(
        f'<tr>'
        f'<td style="padding:9px 16px;font-weight:600;color:#555;white-space:nowrap;'
        f'border-bottom:1px solid #f3f3f3;width:130px;">{k}</td>'
        f'<td style="padding:9px 16px;color:#222;border-bottom:1px solid #f3f3f3;">{v}</td>'
        f'</tr>'
        for k, v in rows
    )
    return f"""<html><body style="margin:0;padding:24px;font-family:Arial,sans-serif;background:#f5f5f5;">
<div style="max-width:580px;margin:0 auto;background:#fff;border-radius:14px;
            box-shadow:0 2px 16px rgba(0,0,0,.09);overflow:hidden;">
  <div style="background:#8b1d72;padding:22px 28px;">
    <h2 style="margin:0;color:#fff;font-size:17px;font-weight:700;">{title}</h2>
  </div>
  <table style="width:100%;border-collapse:collapse;font-size:14px;">{row_html}</table>
  <p style="margin:16px 24px 20px;font-size:12px;color:#bbb;">
    {clinic_name} — internal alert only, please do not reply to this message.
  </p>
</div>
</body></html>"""


def _thanks_html(name: str, clinic_name: str, clinic_email: str, message: str | None) -> str:
    preview_msg = (
        f'<p style="background:#f9f4fd;border-left:4px solid #8b1d72;padding:12px 16px;'
        f'margin:16px 0;border-radius:0 8px 8px 0;font-size:14px;color:#444;">'
        f'{message}</p>'
    ) if message else ""
    return f"""<html><body style="margin:0;padding:24px;font-family:Arial,sans-serif;background:#f5f5f5;">
<div style="max-width:560px;margin:0 auto;background:#fff;border-radius:14px;
            box-shadow:0 2px 16px rgba(0,0,0,.09);overflow:hidden;">
  <div style="background:#8b1d72;padding:22px 28px;">
    <h2 style="margin:0;color:#fff;font-size:17px;font-weight:700;">{clinic_name}</h2>
    <p style="margin:4px 0 0;color:#e8c5e0;font-size:13px;">Thank you for getting in touch</p>
  </div>
  <div style="padding:28px 28px 24px;">
    <p style="font-size:15px;color:#222;margin:0 0 12px;">Dear <strong>{name}</strong>,</p>
    <p style="font-size:14px;color:#555;line-height:1.7;margin:0 0 16px;">
      Thank you for contacting us. We have received your enquiry and a member of our team
      will be in touch with you shortly.
    </p>
    {preview_msg}
    <p style="font-size:14px;color:#555;line-height:1.7;margin:0 0 24px;">
      If you need urgent assistance, please call us directly or reply to this email.
    </p>
    <div style="background:#faf5fd;border-radius:10px;padding:16px 20px;font-size:13px;color:#666;">
      <strong style="color:#8b1d72;">{clinic_name}</strong><br>
      <a href="mailto:{clinic_email}" style="color:#8b1d72;text-decoration:none;">{clinic_email}</a>
    </div>
  </div>
</div>
</body></html>"""


def _send(mail: MailMessage, db: Session) -> None:
    """Send immediately and save result to DB."""
    send_mail_message(mail)
    db.add(mail)


# ── public API ────────────────────────────────────────────────────────────────

def send_booking_alerts(booking: Booking, db: Session) -> None:
    """Send management alert for a new booking (fire-and-save, no queue needed)."""
    clinic_email, cc, bcc, clinic_name = _clinic_cfg(db)
    if not clinic_email:
        return

    service_name  = booking.service.name       if booking.service  else "—"
    staff_name    = booking.staff.name         if booking.staff    else "—"
    patient_name  = booking.patient.full_name  if booking.patient  else "—"
    patient_phone = booking.patient.phone      if booking.patient  else "—"

    rows = [
        ("Booking Code", booking.booking_code or "—"),
        ("Patient",      patient_name),
        ("Phone",        patient_phone),
        ("Service",      service_name),
        ("Staff",        staff_name),
        ("Date",         str(booking.booking_date)),
        ("Time",         booking.booking_time.strftime("%H:%M") if booking.booking_time else "—"),
        ("Status",       booking.status.value if hasattr(booking.status, "value") else str(booking.status)),
        ("Notes",        booking.notes or "—"),
    ]

    alert = MailMessage(
        booking_id=booking.id,
        patient_id=booking.patient_id,
        recipient_email=clinic_email,
        cc_emails=cc,
        bcc_emails=bcc,
        recipient_name="Management",
        subject=f"[New Booking] {patient_name} — {booking.booking_date}",
        body=_alert_html(f"New Booking — {clinic_name}", rows, clinic_name),
        status=MailStatus.queued,
    )
    try:
        _send(alert, db)
    except Exception as exc:
        alert.status = MailStatus.failed
        alert.error_message = str(exc)
        db.add(alert)


def send_contact_alerts(contact: Contact, db: Session) -> None:
    """Send management alert + customer thank-you for a new contact enquiry."""
    clinic_email, cc, bcc, clinic_name = _clinic_cfg(db)

    # 1. Management alert
    if clinic_email:
        rows = [
            ("Name",    contact.full_name),
            ("Phone",   contact.phone),
            ("Email",   contact.email or "—"),
            ("Source",  (contact.source or "—").replace("_", " ").title()),
            ("Message", contact.message or "—"),
        ]
        alert = MailMessage(
            recipient_email=clinic_email,
            cc_emails=cc,
            bcc_emails=bcc,
            recipient_name="Management",
            subject=f"[New Enquiry] {contact.full_name} — {contact.phone}",
            body=_alert_html(f"New Contact Enquiry — {clinic_name}", rows, clinic_name),
            status=MailStatus.queued,
        )
        try:
            _send(alert, db)
        except Exception as exc:
            alert.status = MailStatus.failed
            alert.error_message = str(exc)
            db.add(alert)

    # 2. Customer thank-you (only if they gave their email)
    if contact.email:
        thanks = MailMessage(
            recipient_email=contact.email,
            recipient_name=contact.full_name,
            subject=f"Thank you for contacting {clinic_name}",
            body=_thanks_html(contact.full_name, clinic_name, clinic_email or "", contact.message),
            status=MailStatus.queued,
        )
        try:
            _send(thanks, db)
        except Exception as exc:
            thanks.status = MailStatus.failed
            thanks.error_message = str(exc)
            db.add(thanks)
