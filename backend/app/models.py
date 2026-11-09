from __future__ import annotations
import time
import uuid
from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, JSON, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def uid() -> str:
    return uuid.uuid4().hex

def timestamp() -> int:
    return int(time.time())

class Household(Base):
    __tablename__ = 'households'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[int] = mapped_column(default=timestamp)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    household_id: Mapped[str] = mapped_column(ForeignKey('households.id'), index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(16), default='member')
    email_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=False)
    # This is a household-access state, not account erasure.  The immutable
    # household history continues to reference the person who created or was
    # assigned to a record before access was revoked.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    access_revoked_at: Mapped[int] = mapped_column(Integer, default=0)
    privacy_notice_version: Mapped[str] = mapped_column(String(64), default='')
    privacy_notice_acknowledged_at: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[int] = mapped_column(default=timestamp)
    __table_args__ = (CheckConstraint("role IN ('sender','member')"),)

class LoginSession(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    csrf: Mapped[str] = mapped_column(String(96))
    expires_at: Mapped[int] = mapped_column(Integer)

class Invitation(Base):
    __tablename__ = 'invitations'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    household_id: Mapped[str] = mapped_column(ForeignKey('households.id'))
    email: Mapped[str] = mapped_column(String(254))
    name: Mapped[str] = mapped_column(String(120))
    expires_at: Mapped[int] = mapped_column(Integer)
    used: Mapped[bool] = mapped_column(Boolean, default=False)

class ResetToken(Base):
    __tablename__ = 'reset_tokens'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    expires_at: Mapped[int] = mapped_column(Integer)
    used: Mapped[bool] = mapped_column(Boolean, default=False)

class EmailVerificationToken(Base):
    __tablename__ = 'email_verification_tokens'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    expires_at: Mapped[int] = mapped_column(Integer)
    used: Mapped[bool] = mapped_column(Boolean, default=False)

class Remittance(Base):
    __tablename__ = 'remittances'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    household_id: Mapped[str] = mapped_column(ForeignKey('households.id'), index=True)
    title: Mapped[str] = mapped_column(String(160))
    amount_minor: Mapped[int] = mapped_column(Integer)
    received_on: Mapped[str] = mapped_column(String(10))
    recipient_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    source_currency: Mapped[str] = mapped_column(String(3), default='PHP')
    source_amount: Mapped[str] = mapped_column(String(32), default='')
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[int] = mapped_column(default=timestamp)
    __table_args__ = (CheckConstraint('amount_minor > 0'),)

class Allocation(Base):
    __tablename__ = 'allocations'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    remittance_id: Mapped[str] = mapped_column(ForeignKey('remittances.id'), index=True)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(16), default='expense')
    amount_minor: Mapped[int] = mapped_column(Integer)
    assigned_to: Mapped[str] = mapped_column(ForeignKey('users.id'))
    due_on: Mapped[str] = mapped_column(String(10), default='')
    __table_args__ = (CheckConstraint('amount_minor > 0'), CheckConstraint("kind IN ('expense','savings')"))

class Upload(Base):
    __tablename__ = 'uploads'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    household_id: Mapped[str] = mapped_column(ForeignKey('households.id'), index=True)
    uploader_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    name: Mapped[str] = mapped_column(String(160))
    mime: Mapped[str] = mapped_column(String(64))
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    storage_name: Mapped[str] = mapped_column(String(96))
    extraction: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[int] = mapped_column(default=timestamp)
    __table_args__ = (UniqueConstraint('household_id','sha256'),)

class Evidence(Base):
    __tablename__ = 'evidence'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    household_id: Mapped[str] = mapped_column(ForeignKey('households.id'), index=True)
    remittance_id: Mapped[str] = mapped_column(ForeignKey('remittances.id'), index=True)
    uploader_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    upload_id: Mapped[str | None] = mapped_column(ForeignKey('uploads.id'), unique=True, nullable=True)
    merchant: Mapped[str] = mapped_column(String(160))
    amount_minor: Mapped[int] = mapped_column(Integer)
    occurred_on: Mapped[str] = mapped_column(String(10))
    reference: Mapped[str] = mapped_column(String(120), default='')
    note: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(24), default='pending')
    review_note: Mapped[str] = mapped_column(Text, default='')
    checks: Mapped[list] = mapped_column(JSON, default=list)
    # No writable provider-confirmed flag exists: this build has no bank integration.
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[int] = mapped_column(default=timestamp)
    __table_args__ = (CheckConstraint('amount_minor > 0'), CheckConstraint("status IN ('pending','accepted','clarification','voided')"))
    __mapper_args__ = {'version_id_col': version}

class EvidenceLine(Base):
    __tablename__ = 'evidence_lines'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    evidence_id: Mapped[str] = mapped_column(ForeignKey('evidence.id'), index=True)
    allocation_id: Mapped[str] = mapped_column(ForeignKey('allocations.id'), index=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint('evidence_id','allocation_id'), CheckConstraint('amount_minor > 0'))

class Notification(Base):
    __tablename__ = 'notifications'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    title: Mapped[str] = mapped_column(String(180))
    detail: Mapped[str] = mapped_column(Text)
    remittance_id: Mapped[str] = mapped_column(String(32), default='')
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[int] = mapped_column(default=timestamp)

class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    household_id: Mapped[str] = mapped_column(ForeignKey('households.id'), index=True)
    actor: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(100))
    detail: Mapped[str] = mapped_column(Text)
    remittance_id: Mapped[str] = mapped_column(String(32), default='')
    created_at: Mapped[int] = mapped_column(default=timestamp)

class EmailOutbox(Base):
    __tablename__ = 'email_outbox'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    recipient: Mapped[str] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default='queued')
    next_attempt: Mapped[int] = mapped_column(Integer, default=timestamp)
    created_at: Mapped[int] = mapped_column(default=timestamp)


class Subscription(Base):
    """One commercial subscription per household.

    No payment token, card number, wallet identifier, or raw provider payload is
    stored here.  Xendit retains payment credentials; Padala retains only the
    minimal reconciliation identifiers required to authorize household access.
    """
    __tablename__ = 'subscriptions'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    household_id: Mapped[str] = mapped_column(ForeignKey('households.id'), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(24), default='xendit')
    plan_code: Mapped[str] = mapped_column(String(32), default='monthly')
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default='PHP')
    status: Mapped[str] = mapped_column(String(32), default='pending')
    provider_reference: Mapped[str] = mapped_column(String(64), unique=True)
    provider_customer_id: Mapped[str] = mapped_column(String(96), default='')
    provider_session_id: Mapped[str] = mapped_column(String(96), unique=True, nullable=True)
    provider_plan_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=True)
    checkout_url: Mapped[str] = mapped_column(Text, default='')
    checkout_expires_at: Mapped[int] = mapped_column(Integer, default=0)
    # A plan may be active at Xendit because the payment method was linked,
    # while the first scheduled charge is still one month away. These fields
    # distinguish that trial entitlement from a paid recurring cycle without
    # retaining payment credentials or provider payloads.
    trial_ends_at: Mapped[int] = mapped_column(Integer, default=0)
    trial_started_at: Mapped[int] = mapped_column(Integer, default=0)
    first_payment_confirmed_at: Mapped[int] = mapped_column(Integer, default=0)
    cancel_requested_at: Mapped[int] = mapped_column(Integer, default=0)
    ended_at: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[int] = mapped_column(default=timestamp)
    updated_at: Mapped[int] = mapped_column(default=timestamp, onupdate=timestamp)
    __table_args__ = (
        CheckConstraint('amount_minor > 0'),
        CheckConstraint("provider = 'xendit'"),
        CheckConstraint("currency = 'PHP'"),
        CheckConstraint("status IN ('pending','active','cancellation_pending','canceled','inactive')"),
    )


class BillingWebhookEvent(Base):
    """Idempotency ledger for signed billing callbacks, without raw payloads."""
    __tablename__ = 'billing_webhook_events'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    provider: Mapped[str] = mapped_column(String(24), default='xendit')
    payload_sha256: Mapped[str] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(String(80), default='')
    subscription_id: Mapped[str | None] = mapped_column(ForeignKey('subscriptions.id'), nullable=True)
    outcome: Mapped[str] = mapped_column(String(24), default='ignored')
    received_at: Mapped[int] = mapped_column(default=timestamp)
    __table_args__ = (
        UniqueConstraint('provider', 'payload_sha256'),
        CheckConstraint("provider = 'xendit'"),
        CheckConstraint("outcome IN ('processed','ignored','rejected')"),
    )
