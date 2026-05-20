import smtplib
from email.message import EmailMessage

from app.core.config import get_settings
from app.models.enums import MailStatus
from app.models.mail import MailMessage


def split_emails(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]


def check_smtp_connection() -> dict:
    settings = get_settings()
    result = {
        "configured": bool(settings.smtp_host and settings.smtp_login and settings.smtp_password),
        "host": settings.smtp_host,
        "port": settings.smtp_port,
        "login": settings.smtp_login,
        "from_email": settings.mail_from,
        "use_ssl": settings.smtp_use_ssl,
        "ok": False,
        "error": None,
    }
    if not result["configured"]:
        result["error"] = "SMTP settings are missing"
        return result

    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                smtp.login(settings.smtp_login, settings.smtp_password)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                smtp.starttls()
                smtp.login(settings.smtp_login, settings.smtp_password)
        result["ok"] = True
    except Exception as exc:
        result["error"] = str(exc)
    return result


def send_mail_message(mail: MailMessage) -> MailMessage:
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_login or not settings.smtp_password:
        mail.status = MailStatus.failed
        mail.error_message = "SMTP settings are missing"
        return mail

    to_emails = split_emails(mail.recipient_email)
    cc_emails = split_emails(mail.cc_emails)
    bcc_emails = split_emails(mail.bcc_emails)
    all_recipients = to_emails + cc_emails + bcc_emails
    if not all_recipients:
        mail.status = MailStatus.failed
        mail.error_message = "No recipients found"
        return mail

    message = EmailMessage()
    message["Subject"] = mail.subject
    message["From"] = f"{settings.smtp_from_name} <{settings.mail_from}>"
    message["To"] = ", ".join(to_emails)
    if cc_emails:
        message["Cc"] = ", ".join(cc_emails)
    message.set_content(mail.body)

    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
                smtp.login(settings.smtp_login, settings.smtp_password)
                smtp.send_message(message, from_addr=settings.mail_from, to_addrs=all_recipients)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
                smtp.starttls()
                smtp.login(settings.smtp_login, settings.smtp_password)
                smtp.send_message(message, from_addr=settings.mail_from, to_addrs=all_recipients)
        mail.status = MailStatus.sent
        mail.error_message = None
    except Exception as exc:
        mail.status = MailStatus.failed
        mail.error_message = str(exc)
    return mail
