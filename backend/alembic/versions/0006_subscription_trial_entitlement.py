"""Record Xendit trial end and first paid-cycle confirmation.

Revision ID: 0006_subscription_trial_entitlement
Revises: 0005_xendit_subscriptions
"""
from alembic import op
import sqlalchemy as sa


revision = '0006_subscription_trial_entitlement'
down_revision = '0005_xendit_subscriptions'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('subscriptions', sa.Column('trial_ends_at', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('subscriptions', sa.Column('trial_started_at', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('subscriptions', sa.Column('first_payment_confirmed_at', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('subscriptions', 'first_payment_confirmed_at')
    op.drop_column('subscriptions', 'trial_started_at')
    op.drop_column('subscriptions', 'trial_ends_at')
