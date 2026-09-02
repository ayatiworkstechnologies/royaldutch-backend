import base64
import re
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, parseaddr

import httpx

from app.core.config import get_settings
from app.models.enums import MailStatus
from app.models.mail import MailMessage

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
RESEND_API_URL = "https://api.resend.com/emails"


def split_emails(value: str | None) -> list[str]:
    if not value:
        return []
    emails: list[str] = []
    for item in value.replace(";", ",").split(","):
        parsed = parseaddr(item.strip())[1].strip()
        if parsed:
            emails.append(parsed)
    return emails


def invalid_emails(emails: list[str]) -> list[str]:
    return [email for email in emails if not EMAIL_PATTERN.match(email)]


def is_html_body(value: str) -> bool:
    return "<html" in value.lower() or "<table" in value.lower() or "<body" in value.lower()


def html_to_text(value: str) -> str:
    text = re.sub(r"(?i)<br\s*/?>", "\n", value)
    text = re.sub(r"(?i)</p>|</tr>|</h1>|</h2>|</div>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def check_smtp_connection() -> dict:
    settings = get_settings()
    if settings.resend_api_key:
        result = {
            "provider": "resend",
            "configured": bool(settings.mail_from),
            "from_email": settings.mail_from,
            "ok": False,
            "error": None,
        }
        if not result["configured"]:
            result["error"] = "From email is missing"
            return result
        try:
            response = httpx.get(
                RESEND_API_URL,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                timeout=15,
            )
            result["ok"] = response.status_code < 500
            if not result["ok"]:
                result["error"] = f"Resend API error {response.status_code}"
        except Exception as exc:
            result["error"] = str(exc)
        return result

    result = {
        "provider": "smtp",
        "configured": bool(settings.smtp_host and settings.mail_from),
        "host": settings.smtp_host,
        "port": settings.smtp_port,
        "login": settings.smtp_login,
        "from_email": settings.mail_from,
        "use_ssl": settings.smtp_use_ssl,
        "use_tls": settings.smtp_use_tls,
        "ok": False,
        "error": None,
    }
    if not result["configured"]:
        result["error"] = "SMTP settings are missing"
        return result

    try:
        with smtp_connection() as smtp:
            login_if_configured(smtp)
        result["ok"] = True
    except Exception as exc:
        result["error"] = str(exc)
    return result


def smtp_connection():
    settings = get_settings()
    if settings.smtp_use_ssl:
        return smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30)
    return smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30)


def login_if_configured(smtp) -> None:
    settings = get_settings()
    if not settings.smtp_use_ssl and settings.smtp_use_tls:
        smtp.starttls()
    if settings.smtp_login and settings.smtp_password:
        smtp.login(settings.smtp_login, settings.smtp_password)


def sender_header() -> str:
    settings = get_settings()
    name = settings.smtp_from_name.strip()
    email = settings.mail_from.strip()
    return formataddr((name, email)) if name else email


def send_mail_message(mail: MailMessage, attachments: list[tuple[str, bytes, str]] | None = None) -> MailMessage:
    settings = get_settings()
    if not settings.mail_from:
        mail.status = MailStatus.failed
        mail.error_message = "From email is missing"
        return mail

    to_emails = split_emails(mail.recipient_email)
    cc_emails = split_emails(mail.cc_emails)
    bcc_emails = split_emails(mail.bcc_emails)
    all_recipients = to_emails + cc_emails + bcc_emails
    if not all_recipients:
        mail.status = MailStatus.failed
        mail.error_message = "No recipients found"
        return mail
    bad_emails = invalid_emails(all_recipients + [settings.mail_from])
    if bad_emails:
        mail.status = MailStatus.failed
        mail.error_message = f"Invalid email address: {', '.join(bad_emails)}"
        return mail

    if settings.resend_api_key:
        return _send_via_resend(mail, to_emails, cc_emails, bcc_emails, attachments)
    return _send_via_smtp(mail, to_emails, cc_emails, all_recipients, attachments)


def _send_via_resend(
    mail: MailMessage,
    to_emails: list[str],
    cc_emails: list[str],
    bcc_emails: list[str],
    attachments: list[tuple[str, bytes, str]] | None,
) -> MailMessage:
    settings = get_settings()
    payload: dict = {
        "from": sender_header(),
        "to": to_emails,
        "subject": mail.subject,
    }
    if cc_emails:
        payload["cc"] = cc_emails
    if bcc_emails:
        payload["bcc"] = bcc_emails
    if is_html_body(mail.body):
        payload["html"] = mail.body
        payload["text"] = html_to_text(mail.body)
    else:
        payload["text"] = mail.body
    if attachments:
        payload["attachments"] = [
            {"filename": filename, "content": base64.b64encode(content).decode("ascii")}
            for filename, content, _mime_type in attachments
        ]

    try:
        response = httpx.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json=payload,
            timeout=30,
        )
        if response.status_code >= 400:
            mail.status = MailStatus.failed
            mail.error_message = f"Resend API error {response.status_code}: {response.text[:300]}"
        else:
            mail.status = MailStatus.sent
            mail.error_message = None
    except Exception as exc:
        mail.status = MailStatus.failed
        mail.error_message = str(exc)
    return mail


def _send_via_smtp(
    mail: MailMessage,
    to_emails: list[str],
    cc_emails: list[str],
    all_recipients: list[str],
    attachments: list[tuple[str, bytes, str]] | None,
) -> MailMessage:
    settings = get_settings()
    if not settings.smtp_host:
        mail.status = MailStatus.failed
        mail.error_message = "SMTP host is missing"
        return mail

    message = EmailMessage()
    message["Subject"] = mail.subject
    message["From"] = sender_header()
    message["To"] = ", ".join(to_emails)
    if cc_emails:
        message["Cc"] = ", ".join(cc_emails)
    if is_html_body(mail.body):
        message.set_content(html_to_text(mail.body))
        message.add_alternative(mail.body, subtype="html")
    else:
        message.set_content(mail.body)

    for filename, content, mime_type in attachments or []:
        if "/" not in mime_type:
            mail.status = MailStatus.failed
            mail.error_message = f"Invalid attachment MIME type: {mime_type}"
            return mail
        maintype, subtype = mime_type.split("/", 1)
        message.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)

    try:
        with smtp_connection() as smtp:
            login_if_configured(smtp)
            smtp.send_message(message, from_addr=settings.mail_from, to_addrs=all_recipients)
        mail.status = MailStatus.sent
        mail.error_message = None
    except Exception as exc:
        mail.status = MailStatus.failed
        mail.error_message = str(exc)
    return mail
