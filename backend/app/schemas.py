from __future__ import annotations
import re
from datetime import date
from typing import Annotated, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator, StringConstraints

Money = Annotated[int, Field(strict=True, gt=0, le=1_000_000_000)]
Name = Annotated[str, Field(min_length=1, max_length=120)]
Password = Annotated[str, StringConstraints(strip_whitespace=False), Field(min_length=12, max_length=128)]

class Schema(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class EmailSchema(Schema):
    email: str = Field(max_length=254)
    @field_validator('email')
    @classmethod
    def check_email(cls, v: str):
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', v):
            raise ValueError('Enter a valid email address.')
        return v.lower()

class Login(EmailSchema):
    password: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(min_length=1, max_length=128)

class Register(EmailSchema):
    name: Name
    household_name: Name
    password: Password
    privacy_notice_version: str = Field(default='', max_length=64)

class Invite(EmailSchema):
    name: Name

class AcceptInvite(Schema):
    token: str = Field(min_length=20, max_length=128)
    name: Name
    password: Password
    privacy_notice_version: str = Field(default='', max_length=64)

class PrivacyNoticeAcknowledgement(Schema):
    privacy_notice_version: str = Field(min_length=1, max_length=64)

class ChangePassword(Schema):
    current_password: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(min_length=1, max_length=128)
    new_password: Password

class ResetPassword(Schema):
    token: str = Field(min_length=20, max_length=128)
    password: Password

class VerifyEmail(Schema):
    token: str = Field(min_length=20, max_length=128)

class Preferences(Schema):
    email_notifications: bool

class SubscriptionCheckout(Schema):
    plan_code: Literal['basic', 'family']

class AllocationCreate(Schema):
    name: str = Field(min_length=1, max_length=100)
    kind: Literal['expense', 'savings'] = 'expense'
    amount_minor: Money
    assigned_to: str = Field(min_length=1, max_length=32)
    due_on: date | None = None

class RemittanceCreate(Schema):
    title: str = Field(min_length=1, max_length=160)
    amount_minor: Money
    received_on: date
    recipient_id: str = Field(min_length=1, max_length=32)
    source_currency: str = Field(default='PHP', pattern=r'^[A-Z]{3}$')
    source_amount: str = Field(default='', max_length=32, pattern=r'^(|[0-9]{1,10}(\.[0-9]{1,2})?)$')
    allocations: list[AllocationCreate] = Field(min_length=1, max_length=30)
    @model_validator(mode='after')
    def total_matches(self):
        if sum(a.amount_minor for a in self.allocations) != self.amount_minor:
            raise ValueError('Allocation amounts must add up exactly to the amount received.')
        return self

class EvidenceLineCreate(Schema):
    allocation_id: str = Field(min_length=1, max_length=32)
    amount_minor: Money

class EvidenceCreate(Schema):
    remittance_id: str = Field(min_length=1, max_length=32)
    upload_id: str | None = None
    merchant: str = Field(min_length=1, max_length=160)
    amount_minor: Money
    occurred_on: date
    reference: str = Field(default='', max_length=120)
    note: str = Field(default='', max_length=2000)
    lines: list[EvidenceLineCreate] = Field(min_length=1, max_length=30)
    @model_validator(mode='after')
    def valid_lines(self):
        if sum(l.amount_minor for l in self.lines) != self.amount_minor:
            raise ValueError('Receipt splits must add up exactly to the receipt total.')
        if len({l.allocation_id for l in self.lines}) != len(self.lines):
            raise ValueError('Use each allocation only once per receipt.')
        if not self.upload_id and len(self.note) < 10:
            raise ValueError('Explain the purchase without a receipt in at least 10 characters.')
        return self

class Review(Schema):
    status: Literal['accepted','clarification']
    note: str = Field(default='', max_length=2000)
    expected_version: int = Field(ge=1)
    @model_validator(mode='after')
    def reason_required(self):
        if self.status == 'clarification' and len(self.note) < 3:
            raise ValueError('Explain what needs clarification.')
        return self

class Note(Schema):
    note: str = Field(min_length=3, max_length=2000)
    expected_version: int = Field(ge=1)

class ExtractionRequest(Schema):
    consent: Literal[True]
