from app.core.config import get_settings
from app.models.enums import MailStatus
from app.models.mail import MailMessage
from app.services import smtp_service


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.logged_in = None
        self.sent = None
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def starttls(self):
        self.started_tls = True

    def login(self, username, password):
        self.logged_in = (username, password)

    def send_message(self, message, from_addr, to_addrs):
        self.sent = (message, from_addr, to_addrs)


def configure_smtp(monkeypatch, **values):
    defaults = {
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "mailer@example.com",
        "SMTP_PASSWORD": "secret",
        "SMTP_FROM_EMAIL": "clinic@example.com",
        "SMTP_FROM_NAME": "Royal Dutch Medical Centre",
        "SMTP_USE_SSL": "false",
        "SMTP_USE_TLS": "true",
    }
    defaults.update(values)
    for key, value in defaults.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()


def test_send_mail_message_uses_starttls_and_sends_attachment(monkeypatch):
    configure_smtp(monkeypatch)
    FakeSMTP.instances = []
    monkeypatch.setattr(smtp_service.smtplib, "SMTP", FakeSMTP)

    mail = MailMessage(
        recipient_email="Patient <patient@example.com>",
        cc_emails="accounts@example.com",
        bcc_emails="audit@example.com",
        subject="Invoice ready",
        body="<html><body><h1>Invoice</h1><p>Please find attached.</p></body></html>",
        status=MailStatus.queued,
    )

    smtp_service.send_mail_message(mail, attachments=[("invoice.pdf", b"%PDF-1.4", "application/pdf")])

    assert mail.status == MailStatus.sent
    assert mail.error_message is None
    smtp = FakeSMTP.instances[0]
    assert smtp.started_tls is True
    assert smtp.logged_in == ("mailer@example.com", "secret")
    message, from_addr, to_addrs = smtp.sent
    assert from_addr == "clinic@example.com"
    assert to_addrs == ["patient@example.com", "accounts@example.com", "audit@example.com"]
    assert message["From"] == "Royal Dutch Medical Centre <clinic@example.com>"
    assert "mixed" in message.get_content_type()


def test_send_mail_message_reports_missing_settings(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "")
    monkeypatch.setenv("SMTP_USERNAME", "")
    monkeypatch.setenv("SMTP_USER", "")
    monkeypatch.setenv("SMTP_PASSWORD", "")
    get_settings.cache_clear()

    mail = MailMessage(recipient_email="patient@example.com", subject="Hello", body="Body")

    smtp_service.send_mail_message(mail)

    assert mail.status == MailStatus.failed
    assert mail.error_message == "SMTP host or from email is missing"


def test_send_mail_message_reports_invalid_email(monkeypatch):
    configure_smtp(monkeypatch)

    mail = MailMessage(recipient_email="bad-email", subject="Hello", body="Body")

    smtp_service.send_mail_message(mail)

    assert mail.status == MailStatus.failed
    assert "Invalid email address" in mail.error_message
