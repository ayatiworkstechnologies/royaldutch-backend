from enum import StrEnum


class RecordStatus(StrEnum):
    active = "active"
    inactive = "inactive"


class BookingStatus(StrEnum):
    pending = "pending"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"
    rescheduled = "rescheduled"


class PaymentMethod(StrEnum):
    pay_at_clinic = "pay_at_clinic"
    online = "online"
    advance = "advance"
    full = "full"


class PaymentStatus(StrEnum):
    unpaid = "unpaid"
    partially_paid = "partially_paid"
    paid = "paid"
    refunded = "refunded"


class InvoiceStatus(StrEnum):
    draft = "draft"
    issued = "issued"
    partially_paid = "partially_paid"
    paid = "paid"
    cancelled = "cancelled"
    refunded = "refunded"


class NotificationChannel(StrEnum):
    email = "email"
    whatsapp = "whatsapp"
    sms = "sms"
    dashboard = "dashboard"


class NotificationStatus(StrEnum):
    queued = "queued"
    sent = "sent"
    failed = "failed"


class MailStatus(StrEnum):
    draft = "draft"
    queued = "queued"
    sent = "sent"
    failed = "failed"
