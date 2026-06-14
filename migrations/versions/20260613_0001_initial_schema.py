"""initial explicit schema

Revision ID: 20260613_0001
Revises:
Create Date: 2026-06-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260613_0001"
down_revision = None
branch_labels = None
depends_on = None


booking_status = sa.Enum("pending", "confirmed", "completed", "cancelled", "no_show", "rescheduled", name="bookingstatus")
invoice_status = sa.Enum("draft", "issued", "partially_paid", "paid", "cancelled", "refunded", name="invoicestatus")
mail_status = sa.Enum("draft", "queued", "processing", "sent", "failed", name="mailstatus")
notification_channel = sa.Enum("email", "whatsapp", "sms", "dashboard", name="notificationchannel")
notification_status = sa.Enum("queued", "sent", "failed", name="notificationstatus")
payment_method = sa.Enum("pay_at_clinic", "online", "advance", "full", name="paymentmethod")
payment_status = sa.Enum("unpaid", "partially_paid", "paid", "refunded", name="paymentstatus")
record_status = sa.Enum("active", "inactive", name="recordstatus")


def upgrade() -> None:
    existing_tables = set(inspect(op.get_bind()).get_table_names())
    if "users" in existing_tables:
        raise RuntimeError(
            "Existing schema detected: table 'users' already exists, so the initial Alembic "
            "create-table migration must not be run on this database. Run "
            "`python scripts/verify_schema_for_stamp.py`; if verification passes, run "
            "`alembic stamp head`. After stamping, future `alembic upgrade head` commands "
            "will work normally."
        )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("email", sa.String(180), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("entity_type", sa.String(120), nullable=False),
        sa.Column("entity_id", sa.String(80), nullable=True),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(80), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])

    op.create_table(
        "auth_otps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(180), nullable=False),
        sa.Column("code_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_auth_otps_id", "auth_otps", ["id"])
    op.create_index("ix_auth_otps_email", "auth_otps", ["email"])

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", record_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_categories_id", "categories", ["id"])
    op.create_index("ix_categories_external_id", "categories", ["external_id"], unique=True)
    op.create_index("ix_categories_slug", "categories", ["slug"], unique=True)
    op.create_index("ix_categories_name", "categories", ["name"], unique=True)

    op.create_table(
        "clinic_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_clinic_settings_id", "clinic_settings", ["id"])
    op.create_index("ix_clinic_settings_key", "clinic_settings", ["key"], unique=True)

    op.create_table(
        "email_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("subject", sa.String(220), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", record_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_email_templates_id", "email_templates", ["id"])
    op.create_index("ix_email_templates_slug", "email_templates", ["slug"], unique=True)

    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(180), nullable=False),
        sa.Column("email", sa.String(180), nullable=True),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("gender", sa.String(30), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("documents", sa.String(1000), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_patients_id", "patients", ["id"])
    op.create_index("ix_patients_email", "patients", ["email"])
    op.create_index("ix_patients_phone", "patients", ["phone"], unique=True)
    op.create_index("ix_patients_user_id", "patients", ["user_id"])

    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.Integer(), nullable=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("slug", sa.String(220), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("image", sa.String(500), nullable=True),
        sa.Column("status", record_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_services_id", "services", ["id"])
    op.create_index("ix_services_external_id", "services", ["external_id"], unique=True)
    op.create_index("ix_services_category_id", "services", ["category_id"])
    op.create_index("ix_services_slug", "services", ["slug"], unique=True)

    op.create_table(
        "staff",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("email", sa.String(180), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("role", sa.String(100), nullable=False),
        sa.Column("specialization", sa.String(180), nullable=True),
        sa.Column("profile_image", sa.String(500), nullable=True),
        sa.Column("status", record_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_staff_id", "staff", ["id"])
    op.create_index("ix_staff_email", "staff", ["email"], unique=True)

    op.create_table(
        "staff_services",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("staff.id"), nullable=False),
        sa.Column("service_id", sa.Integer(), sa.ForeignKey("services.id"), nullable=False),
        sa.UniqueConstraint("staff_id", "service_id", name="uq_staff_service"),
    )
    op.create_index("ix_staff_services_staff_id", "staff_services", ["staff_id"])
    op.create_index("ix_staff_services_service_id", "staff_services", ["service_id"])

    op.create_table(
        "staff_availability",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("staff.id"), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("break_start_time", sa.Time(), nullable=True),
        sa.Column("break_end_time", sa.Time(), nullable=True),
        sa.Column("status", record_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_staff_availability_id", "staff_availability", ["id"])
    op.create_index("ix_staff_availability_staff_id", "staff_availability", ["staff_id"])

    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_code", sa.String(30), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("service_id", sa.Integer(), sa.ForeignKey("services.id"), nullable=False),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("staff.id"), nullable=True),
        sa.Column("booking_date", sa.Date(), nullable=False),
        sa.Column("booking_time", sa.Time(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("status", booking_status, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("first_visit", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_bookings_id", "bookings", ["id"])
    op.create_index("ix_bookings_booking_code", "bookings", ["booking_code"], unique=True)
    op.create_index("ix_bookings_patient_id", "bookings", ["patient_id"])
    op.create_index("ix_bookings_service_id", "bookings", ["service_id"])
    op.create_index("ix_bookings_staff_id", "bookings", ["staff_id"])
    op.create_index("ix_bookings_booking_date", "bookings", ["booking_date"])
    op.create_index("ix_bookings_status", "bookings", ["status"])
    op.create_index("ix_bookings_staff_date_status", "bookings", ["staff_id", "booking_date", "status"])

    op.create_table(
        "booking_slot_locks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("staff.id"), nullable=False),
        sa.Column("booking_date", sa.Date(), nullable=False),
        sa.Column("booking_time", sa.Time(), nullable=False),
        sa.Column("lock_key", sa.String(120), nullable=False),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("staff_id", "booking_date", "booking_time", name="uq_booking_slot_lock"),
    )
    op.create_index("ix_booking_slot_locks_id", "booking_slot_locks", ["id"])
    op.create_index("ix_booking_slot_locks_staff_id", "booking_slot_locks", ["staff_id"])
    op.create_index("ix_booking_slot_locks_booking_date", "booking_slot_locks", ["booking_date"])
    op.create_index("ix_booking_slot_locks_lock_key", "booking_slot_locks", ["lock_key"], unique=True)
    op.create_index("ix_booking_slot_locks_booking_id", "booking_slot_locks", ["booking_id"])
    op.create_index("ix_booking_slot_locks_staff_date", "booking_slot_locks", ["staff_id", "booking_date"])

    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_number", sa.String(40), nullable=False),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("balance_due", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("status", invoice_status, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("booking_id", name="uq_invoices_booking_id"),
    )
    op.create_index("ix_invoices_id", "invoices", ["id"])
    op.create_index("ix_invoices_invoice_number", "invoices", ["invoice_number"], unique=True)
    op.create_index("ix_invoices_booking_id", "invoices", ["booking_id"])
    op.create_index("ix_invoices_patient_id", "invoices", ["patient_id"])

    op.create_table(
        "invoice_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("description", sa.String(250), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_invoice_items_id", "invoice_items", ["id"])
    op.create_index("ix_invoice_items_invoice_id", "invoice_items", ["invoice_id"])

    op.create_table(
        "mail_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=True),
        sa.Column("recipient_email", sa.String(180), nullable=False),
        sa.Column("cc_emails", sa.String(1000), nullable=True),
        sa.Column("bcc_emails", sa.String(1000), nullable=True),
        sa.Column("recipient_name", sa.String(180), nullable=True),
        sa.Column("subject", sa.String(220), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", mail_status, nullable=False),
        sa.Column("provider_message_id", sa.String(220), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lock_token", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_mail_messages_id", "mail_messages", ["id"])
    op.create_index("ix_mail_messages_booking_id", "mail_messages", ["booking_id"])
    op.create_index("ix_mail_messages_patient_id", "mail_messages", ["patient_id"])
    op.create_index("ix_mail_messages_invoice_id", "mail_messages", ["invoice_id"])
    op.create_index("ix_mail_messages_lock_token", "mail_messages", ["lock_token"])
    op.create_index("ix_mail_queue_scan", "mail_messages", ["status", "retry_count", "created_at", "locked_at"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=True),
        sa.Column("channel", notification_channel, nullable=False),
        sa.Column("recipient", sa.String(180), nullable=False),
        sa.Column("subject", sa.String(180), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", notification_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_id", "notifications", ["id"])
    op.create_index("ix_notifications_booking_id", "notifications", ["booking_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("refund_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("payment_method", payment_method, nullable=False),
        sa.Column("payment_status", payment_status, nullable=False),
        sa.Column("transaction_id", sa.String(180), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_payments_id", "payments", ["id"])
    op.create_index("ix_payments_booking_id", "payments", ["booking_id"])
    op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"])
    op.create_index("ix_payments_transaction_id", "payments", ["transaction_id"], unique=True)


def downgrade() -> None:
    for table in [
        "payments",
        "notifications",
        "mail_messages",
        "invoice_items",
        "invoices",
        "booking_slot_locks",
        "bookings",
        "staff_availability",
        "staff_services",
        "staff",
        "services",
        "patients",
        "email_templates",
        "clinic_settings",
        "categories",
        "auth_otps",
        "audit_logs",
        "users",
    ]:
        op.drop_table(table)
