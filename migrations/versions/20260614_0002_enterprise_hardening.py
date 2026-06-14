"""enterprise hardening modules

Revision ID: 20260614_0002
Revises: 20260613_0001
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa

revision = "20260614_0002"
down_revision = "20260613_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_token_id", sa.Integer(), sa.ForeignKey("refresh_tokens.id"), nullable=True),
        sa.Column("created_by_ip", sa.String(80), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_refresh_tokens_id", "refresh_tokens", ["id"])
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])

    op.create_table(
        "patient_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("document_type", sa.String(80), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=True),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("external_url", sa.String(1000), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_patient_documents_id", "patient_documents", ["id"])
    op.create_index("ix_patient_documents_patient_id", "patient_documents", ["patient_id"])
    op.create_index("ix_patient_documents_document_type", "patient_documents", ["document_type"])
    op.create_index("ix_patient_documents_storage_key", "patient_documents", ["storage_key"], unique=True)
    op.create_index("ix_patient_documents_uploaded_by_user_id", "patient_documents", ["uploaded_by_user_id"])

    op.create_table(
        "whatsapp_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("notification_id", sa.Integer(), sa.ForeignKey("notifications.id"), nullable=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("recipient_phone", sa.String(40), nullable=False),
        sa.Column("template", sa.String(120), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("provider", sa.String(80), nullable=True),
        sa.Column("provider_message_id", sa.String(220), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_whatsapp_messages_id", "whatsapp_messages", ["id"])
    op.create_index("ix_whatsapp_messages_notification_id", "whatsapp_messages", ["notification_id"])
    op.create_index("ix_whatsapp_messages_booking_id", "whatsapp_messages", ["booking_id"])
    op.create_index("ix_whatsapp_messages_patient_id", "whatsapp_messages", ["patient_id"])
    op.create_index("ix_whatsapp_messages_recipient_phone", "whatsapp_messages", ["recipient_phone"])
    op.create_index("ix_whatsapp_messages_status", "whatsapp_messages", ["status"])


def downgrade() -> None:
    op.drop_table("whatsapp_messages")
    op.drop_table("patient_documents")
    op.drop_table("refresh_tokens")
