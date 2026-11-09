"""Add Xendit subscription lifecycle and webhook idempotency records.

Revision ID: 0005_xendit_subscriptions
Revises: 0004_household_member_access
"""
from alembic import op
import sqlalchemy as sa


revision = '0005_xendit_subscriptions'
down_revision = '0004_household_member_access'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('household_id', sa.String(length=32), nullable=False),
        sa.Column('provider', sa.String(length=24), nullable=False, server_default='xendit'),
        sa.Column('plan_code', sa.String(length=32), nullable=False, server_default='monthly'),
        sa.Column('amount_minor', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='PHP'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('provider_reference', sa.String(length=64), nullable=False),
        sa.Column('provider_customer_id', sa.String(length=96), nullable=False, server_default=''),
        sa.Column('provider_session_id', sa.String(length=96), nullable=True),
        sa.Column('provider_plan_id', sa.String(length=128), nullable=True),
        sa.Column('checkout_url', sa.Text(), nullable=False, server_default=''),
        sa.Column('checkout_expires_at', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cancel_requested_at', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ended_at', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.Integer(), nullable=False),
        sa.CheckConstraint('amount_minor > 0'),
        sa.CheckConstraint("provider = 'xendit'"),
        sa.CheckConstraint("currency = 'PHP'"),
        sa.CheckConstraint("status IN ('pending','active','cancellation_pending','canceled','inactive')"),
        sa.ForeignKeyConstraint(['household_id'], ['households.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('household_id'),
        sa.UniqueConstraint('provider_reference'),
        sa.UniqueConstraint('provider_session_id'),
        sa.UniqueConstraint('provider_plan_id'),
    )
    op.create_index('ix_subscriptions_household_id', 'subscriptions', ['household_id'])
    op.create_table(
        'billing_webhook_events',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('provider', sa.String(length=24), nullable=False, server_default='xendit'),
        sa.Column('payload_sha256', sa.String(length=64), nullable=False),
        sa.Column('event_type', sa.String(length=80), nullable=False, server_default=''),
        sa.Column('subscription_id', sa.String(length=32), nullable=True),
        sa.Column('outcome', sa.String(length=24), nullable=False, server_default='ignored'),
        sa.Column('received_at', sa.Integer(), nullable=False),
        sa.CheckConstraint("provider = 'xendit'"),
        sa.CheckConstraint("outcome IN ('processed','ignored','rejected')"),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'payload_sha256'),
    )


def downgrade():
    op.drop_table('billing_webhook_events')
    op.drop_index('ix_subscriptions_household_id', table_name='subscriptions')
    op.drop_table('subscriptions')
