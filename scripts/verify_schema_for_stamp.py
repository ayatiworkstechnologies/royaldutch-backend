from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import engine


REQUIRED_COLUMNS = {
    "users": {"id", "name", "email", "hashed_password", "role", "is_active", "created_at", "updated_at"},
    "audit_logs": {"id", "user_id", "action", "entity_type", "entity_id", "old_value", "new_value", "ip_address", "user_agent", "request_id", "created_at", "updated_at"},
    "auth_otps": {"id", "email", "code_hash", "expires_at", "used", "created_at", "updated_at"},
    "categories": {"id", "external_id", "name", "slug", "description", "status", "created_at", "updated_at"},
    "clinic_settings": {"id", "key", "value", "created_at", "updated_at"},
    "email_templates": {"id", "name", "slug", "description", "subject", "body", "status", "created_at", "updated_at"},
    "patients": {"id", "full_name", "email", "phone", "gender", "age", "notes", "documents", "user_id", "created_at", "updated_at"},
    "services": {"id", "external_id", "category_id", "name", "slug", "description", "duration_minutes", "price", "currency", "image", "status", "created_at", "updated_at"},
    "staff": {"id", "name", "email", "phone", "role", "specialization", "profile_image", "status", "created_at", "updated_at"},
    "staff_services": {"id", "staff_id", "service_id"},
    "staff_availability": {"id", "staff_id", "day_of_week", "start_time", "end_time", "break_start_time", "break_end_time", "status", "created_at", "updated_at"},
    "bookings": {"id", "booking_code", "patient_id", "service_id", "staff_id", "booking_date", "booking_time", "duration_minutes", "price", "currency", "status", "notes", "first_visit", "created_at", "updated_at"},
    "booking_slot_locks": {"id", "staff_id", "booking_date", "booking_time", "lock_key", "booking_id", "created_at", "updated_at"},
    "invoices": {"id", "invoice_number", "booking_id", "patient_id", "issue_date", "due_date", "subtotal", "discount_amount", "tax_amount", "total_amount", "paid_amount", "balance_due", "currency", "status", "notes", "created_at", "updated_at"},
    "invoice_items": {"id", "invoice_id", "description", "quantity", "unit_price", "line_total", "created_at", "updated_at"},
    "mail_messages": {"id", "booking_id", "patient_id", "invoice_id", "recipient_email", "cc_emails", "bcc_emails", "recipient_name", "subject", "body", "status", "provider_message_id", "error_message", "retry_count", "last_attempt_at", "locked_at", "lock_token", "created_at", "updated_at"},
    "notifications": {"id", "booking_id", "channel", "recipient", "subject", "message", "status", "created_at", "updated_at"},
    "payments": {"id", "booking_id", "invoice_id", "amount", "refund_amount", "payment_method", "payment_status", "transaction_id", "created_at", "updated_at"},
}


REQUIRED_INDEXES = {
    "bookings": {"ix_bookings_staff_date_status"},
    "booking_slot_locks": {"ix_booking_slot_locks_staff_date", "ix_booking_slot_locks_lock_key"},
    "mail_messages": {"ix_mail_queue_scan", "ix_mail_messages_lock_token"},
}


def main() -> int:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    errors: list[str] = []

    for table, required_columns in REQUIRED_COLUMNS.items():
        if table not in existing_tables:
            errors.append(f"Missing table: {table}")
            continue
        existing_columns = {column["name"] for column in inspector.get_columns(table)}
        missing_columns = sorted(required_columns - existing_columns)
        if missing_columns:
            errors.append(f"{table}: missing columns: {', '.join(missing_columns)}")

    for table, required_indexes in REQUIRED_INDEXES.items():
        if table not in existing_tables:
            continue
        existing_indexes = {index["name"] for index in inspector.get_indexes(table)}
        missing_indexes = sorted(required_indexes - existing_indexes)
        if missing_indexes:
            errors.append(f"{table}: missing indexes: {', '.join(missing_indexes)}")

    if "alembic_version" in existing_tables:
        with engine.connect() as connection:
            version = connection.execute(text("select version_num from alembic_version")).scalar()
        print(f"Database already has alembic_version={version}")
        return 0

    if errors:
        print("Schema verification failed. Do not run 'alembic stamp head' yet.")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Schema verification passed.")
    print("This existing database can be stamped with:")
    print("  alembic stamp head")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
